/**
 * Reader for the Afer member area.
 *
 * Only the site's pages and XPaths live here; everything else is the launcher's.
 * The XPaths are the ones of woob's abeilleassurances module, which Afer's
 * site is built on.
 *
 * `read` is serialised into the bookmarklet with `toString()`: every helper it
 * needs is declared inside its body, nothing may come from this module.
 */

import type { Io, SourceAccount, SourceLine, SourceSnapshot } from './bookmarklet.js';

export async function read(io: Io): Promise<SourceSnapshot> {
	const IGNORED = [
		'Prévoyance',
		'Responsabilité civile',
		'Complémentaire santé',
		'Protection juridique',
		'Habitation',
		'Automobile'
	];

	const clean = (value: string | null | undefined) => (value ?? '').replace(/\s+/g, ' ').trim();
	const hasClass = (name: string) =>
		`contains(concat(' ', normalize-space(@class), ' '), ' ${name} ')`;
	const doc = (ctx: Node) => (ctx.ownerDocument ?? ctx) as Document;
	// 9 and 7: XPathResult.FIRST_ORDERED_NODE_TYPE and ORDERED_NODE_SNAPSHOT_TYPE.
	const one = (ctx: Node, xpath: string) =>
		doc(ctx).evaluate(xpath, ctx, null, 9, null).singleNodeValue;
	const all = (ctx: Node, xpath: string) => {
		const found = doc(ctx).evaluate(xpath, ctx, null, 7, null);
		const nodes: Node[] = [];
		for (let i = 0; i < found.snapshotLength; i++) nodes.push(found.snapshotItem(i) as Node);
		return nodes;
	};
	const text = (ctx: Node, xpath: string) => clean(one(ctx, xpath)?.textContent);
	const ownText = (ctx: Node, xpath: string) =>
		clean(
			all(ctx, `${xpath}/text()`)
				.map((n) => n.textContent)
				.join(' ')
		);
	const number = (value: string): number | null => {
		const digits = value
			.replace(/[^\d,.-]/g, '')
			.replace(/\./g, '')
			.replace(',', '.');
		const parsed = digits === '' ? NaN : Number(digits);
		return Number.isFinite(parsed) ? parsed : null;
	};
	const first = (values: string[]) => values.find((v) => v !== '') ?? '';
	const date = (value: string) => {
		const m = /(\d{2})\/(\d{2})\/(\d{4})/.exec(value);
		return m ? `${m[3]}-${m[2]}-${m[1]}` : null;
	};
	const load = async (url: string) => {
		const html = new DOMParser().parseFromString(await (await io.fetch(url)).text(), 'text/html');
		if (html.querySelector('form#loginForm')) {
			throw new Error('the Afer session has ended. Log in again, then click the bookmark.');
		}
		return html;
	};

	const summaryUrl = `${new URL(io.here).origin}/espaceadherent/Accueil/Synthese-Contrats`;
	const summary = await load(summaryUrl);

	const items = all(
		summary,
		'//div[contains(@class, "o-product-roundels")]/div[@data-policy]'
	).filter(
		(item) =>
			!IGNORED.includes(text(item, `../../div[${hasClass('o-product-tab-category')}]`))
	);

	const seen = new Map<string, number>();
	const accounts: SourceAccount[] = [];
	for (const item of items) {
		let label = text(item, `.//p[${hasClass('a-heading')}]`) || 'Contract';
		const count = (seen.get(label) ?? 0) + 1;
		seen.set(label, count);
		if (count > 1) label = `${label} (${count})`;

		const href = (
			one(
				item,
				'.//a[contains(text(), "Détail") or contains(text(), "Mon adhésion") or contains(text(), "Ma situation")]/@href'
			) as Attr | null
		)?.value;
		if (!href) {
			accounts.push({ label, product: '', balance: null, available: false, lines: [] });
			continue;
		}
		const detail = await load(new URL(href, summaryUrl).href);

		const product = text(detail, '//h3[contains(text(), "Type de produit")]/following-sibling::p');
		const balance = number(
			first(
				[
					'//h3[contains(text(), "Valeur de rachat")]/following-sibling::p/strong',
					'//h3[contains(text(), "pargne retraite")]/following-sibling::p/strong',
					'//h3[contains(text(), "Capital constitutif de rente")]/following-sibling::p',
					'//h2[contains(text(), "pargne constituée")]/span',
					'//h2[contains(text(), "pargne disponible")]/span',
					'//h2[contains(text(), "Valeur de rachat")]/span',
					'//h2[contains(text(), "pargne retraite")]/span',
					'//h2[contains(text(), "Capital constitutif de rente")]/span',
					'//li[h3[contains(text(), "pargne constituée")]]/p/strong',
					'//h3[contains(text(), "pargne disponible")]/following-sibling::p'
				].map((xpath) => text(detail, xpath))
			)
		);
		const available = !one(
			detail,
			'//p[contains(text(), "est pas disponible") or contains(text(), "est pas possible")]'
		);

		const cell = (name: string) =>
			`./td[contains(@data-label, "${name}") or contains(@data-th, "${name}")]`;
		const lines: SourceLine[] = [];
		for (const row of all(
			detail,
			'//div[contains(@class, "m-table")]//table[.//th[contains(., "Valeur de la part")]]/tbody/tr[not(contains(@class, "total")) and count(td) > 3]'
		)) {
			const name = first([
				text(row, './th[contains(@data-label, "Nom du su")]/a'),
				text(row, './th[contains(@data-label, "Nom du su")]'),
				text(row, './td[contains(@data-label, "Nom du su")]'),
				text(row, './th[1]')
			]);
			if (name === '' || name === 'Total') continue;
			lines.push({
				label: name,
				quantity: number(text(row, cell('Nombre de parts'))),
				unit_value: number(text(row, cell('Valeur de la part'))),
				valuation: number(
					first([
						text(row, './td[contains(@data-label, "Valeur de rachat")]'),
						ownText(row, './td[contains(@data-label, "Montant")]'),
						text(row, './td[contains(@data-th, "Montant")]')
					])
				),
				invested: number(text(row, cell('Prime investie'))),
				value_date: date(
					text(row, './td[@data-label="Date de valeur" or @data-th="Date de valeur"]')
				),
				by_amount: true
			});
		}

		accounts.push({ label, product, balance, available, lines });
	}

	return { source: 'afer', version: 1, read_on: new Date().toISOString().slice(0, 10), accounts };
}

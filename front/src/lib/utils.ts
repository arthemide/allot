import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

// Type helpers expected by the shadcn-svelte components in ui/.
export type WithoutChild<T> = T extends { child?: unknown } ? Omit<T, 'child'> : T;
export type WithoutChildren<T> = T extends { children?: unknown } ? Omit<T, 'children'> : T;
export type WithoutChildrenOrChild<T> = WithoutChildren<WithoutChild<T>>;
export type WithElementRef<T, U extends HTMLElement = HTMLElement> = T & {
	ref?: U | null;
};

const CURRENCY_SYMBOLS: Record<string, string> = {
	USD: '$',
	EUR: '€'
};

export function currencySymbol(currency: string | null | undefined): string {
	if (!currency) return '€';
	return CURRENCY_SYMBOLS[currency.toUpperCase()] ?? currency;
}

export function formatMoney(
	value: number | null | undefined,
	currency: string | null | undefined,
	fractionDigits = 2
): string {
	if (value === null || value === undefined) return '-';
	const amount = value.toLocaleString('fr-FR', {
		minimumFractionDigits: fractionDigits,
		maximumFractionDigits: fractionDigits
	});
	return `${amount} ${currencySymbol(currency)}`;
}

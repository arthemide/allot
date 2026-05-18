import { type ClassValue, clsx } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
	return twMerge(clsx(inputs));
}

const CURRENCY_SYMBOLS: Record<string, string> = {
	USD: '$',
	EUR: '€',
};

export function currencySymbol(currency: string | null | undefined): string {
	if (!currency) return '$';
	return CURRENCY_SYMBOLS[currency.toUpperCase()] ?? currency;
}

export function formatMoney(
	value: number | null | undefined,
	currency: string | null | undefined,
	fractionDigits = 2
): string {
	if (value === null || value === undefined) return 'N/A';
	return `${value.toFixed(fractionDigits)}${currencySymbol(currency)}`;
}

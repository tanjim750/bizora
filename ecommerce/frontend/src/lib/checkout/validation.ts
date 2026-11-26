import type {
  Money,
  StoreConfig,
  PlaceOrderBody,
} from '@/lib/api/types';

export type CheckoutFormValues = {
  email: string;
  phone: string;
  firstName: string;
  lastName: string;
  line1: string;
  line2: string;
  city: string;
  postalCode: string;
  countryCode: string;
  shippingMethodId: string;
  paymentMethodId: string;
  note: string;
};

export const CHECKOUT_FIELDS: readonly (keyof CheckoutFormValues)[] = [
  'email',
  'phone',
  'firstName',
  'lastName',
  'line1',
  'line2',
  'city',
  'postalCode',
  'countryCode',
  'shippingMethodId',
  'paymentMethodId',
  'note',
] as const;

export function emptyCheckoutValues(
  store: StoreConfig,
  email = '',
): CheckoutFormValues {
  return {
    email,
    phone: '',
    firstName: '',
    lastName: '',
    line1: '',
    line2: '',
    city: '',
    postalCode: '',
    countryCode: store.countries[0]?.code ?? '',
    shippingMethodId: store.shippingMethods[0]?.id ?? '',
    paymentMethodId: store.paymentMethods.find((m) => m.enabled)?.id ?? '',
    note: '',
  };
}

const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const phoneRegex = /^\+?[0-9 ()-]{7,20}$/;
const postalCodeRegex = /^[A-Za-z0-9 -]{3,10}$/;

export function validateField(
  name: keyof CheckoutFormValues,
  values: CheckoutFormValues,
  store: StoreConfig,
): string | undefined {
  const val = (values[name] ?? '').trim();

  switch (name) {
    case 'email':
      if (!val) return 'Enter your email address.';
      if (!emailRegex.test(val)) return 'Enter a valid email address.';
      return undefined;

    case 'phone':
      if (!val || !phoneRegex.test(val)) return 'Enter a phone number we can call.';
      return undefined;

    case 'firstName':
      if (!val) return 'Enter your first name.';
      return undefined;

    case 'lastName':
      if (!val) return 'Enter your last name.';
      return undefined;

    case 'line1':
      if (val.length < 3) return 'Enter your street address.';
      return undefined;

    case 'line2':
      if (val.length > 120) return 'Keep this under 120 characters.';
      return undefined;

    case 'city':
      if (val.length < 2) return 'Enter your city.';
      return undefined;

    case 'postalCode':
      if (!postalCodeRegex.test(val)) return 'Enter a valid postal code.';
      return undefined;

    case 'countryCode':
      if (!store.countries.some((c) => c.code === val)) return 'Choose a country.';
      return undefined;

    case 'shippingMethodId':
      if (!store.shippingMethods.some((m) => m.id === val))
        return 'Choose a delivery method.';
      return undefined;

    case 'paymentMethodId':
      if (!store.paymentMethods.some((m) => m.id === val && m.enabled))
        return 'Choose a payment method.';
      return undefined;

    case 'note':
      if (val.length > 500) return 'Keep the note under 500 characters.';
      return undefined;

    default:
      return undefined;
  }
}

export function validateCheckout(
  values: CheckoutFormValues,
  store: StoreConfig,
):
  | { ok: true; body: Omit<PlaceOrderBody, 'expectedTotal'> }
  | { ok: false; errors: Partial<Record<keyof CheckoutFormValues, string>> } {
  const errors: Partial<Record<keyof CheckoutFormValues, string>> = {};

  for (const field of CHECKOUT_FIELDS) {
    const err = validateField(field, values, store);
    if (err) {
      errors[field] = err;
    }
  }

  if (Object.keys(errors).length > 0) {
    return { ok: false, errors };
  }

  const line2Raw = (values.line2 ?? '').trim();
  const noteRaw = (values.note ?? '').trim();

  const body: Omit<PlaceOrderBody, 'expectedTotal'> = {
    email: values.email.trim(),
    phone: values.phone.trim(),
    shippingAddress: {
      firstName: values.firstName.trim(),
      lastName: values.lastName.trim(),
      line1: values.line1.trim(),
      line2: line2Raw ? line2Raw : null,
      city: values.city.trim(),
      postalCode: values.postalCode.trim(),
      countryCode: values.countryCode.trim(),
    },
    shippingMethodId: values.shippingMethodId.trim(),
    paymentMethodId: values.paymentMethodId.trim(),
    note: noteRaw ? noteRaw : null,
  };

  return { ok: true, body };
}

export function toPlaceOrderBody(
  body: Omit<PlaceOrderBody, 'expectedTotal'>,
  expectedTotal: Money,
): PlaceOrderBody {
  return {
    ...body,
    expectedTotal,
  };
}

export function mapApiFieldErrors(
  fields: Record<string, string[]> | null | undefined,
): Partial<Record<keyof CheckoutFormValues, string>> {
  if (!fields) return {};
  const mapping: Record<string, keyof CheckoutFormValues> = {
    email: 'email',
    phone: 'phone',
    'shippingAddress.firstName': 'firstName',
    'shippingAddress.lastName': 'lastName',
    'shippingAddress.line1': 'line1',
    'shippingAddress.line2': 'line2',
    'shippingAddress.city': 'city',
    'shippingAddress.postalCode': 'postalCode',
    'shippingAddress.countryCode': 'countryCode',
    shippingMethodId: 'shippingMethodId',
    paymentMethodId: 'paymentMethodId',
    note: 'note',
  };

  const result: Partial<Record<keyof CheckoutFormValues, string>> = {};
  for (const [apiKey, formKey] of Object.entries(mapping)) {
    const msgs = fields[apiKey];
    if (msgs && msgs.length > 0 && msgs[0]) {
      result[formKey] = msgs[0];
    }
  }
  return result;
}

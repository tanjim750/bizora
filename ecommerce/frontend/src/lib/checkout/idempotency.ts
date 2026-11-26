export function newIdempotencyKey(): string {
  return crypto.randomUUID();
}

export function createAttemptKeys(): { current(): string; renew(): string } {
  let key = newIdempotencyKey();
  return {
    current: () => key,
    renew: () => {
      key = newIdempotencyKey();
      return key;
    },
  };
}

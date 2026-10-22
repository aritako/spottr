/** Read the first non-file value from FormData, trimmed. */
export function readStringField(data: FormData, ...names: string[]): string {
  for (const name of names) {
    const value = data.get(name);
    if (typeof value === "string") return value.trim();
  }
  return "";
}

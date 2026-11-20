export interface Sub2APISelection {
  key_id: number;
  model_id: string;
}

export interface Sub2APISession {
  user_id: number | null;
  authorized: boolean;
}

export interface Sub2APIKey {
  id: number;
  name: string;
  mask: string;
  group_name: string;
  platform: string;
  status: string;
  selectable: boolean;
}

export interface Sub2APIModel {
  id: string;
}

type SavedSelection = { keyID: number | null; models: Record<number, string> };

function selectionStorageKey(userID: number) {
  return `sub2api-chat-selection:v1:${userID}`;
}

export function readSelection(userID: number): SavedSelection {
  try {
    const saved: Partial<SavedSelection> | null = JSON.parse(
      localStorage.getItem(selectionStorageKey(userID)) ?? "null"
    );
    if (
      saved &&
      typeof saved === "object" &&
      saved.models &&
      typeof saved.models === "object"
    ) {
      return {
        keyID:
          Number.isSafeInteger(saved.keyID) && saved.keyID! > 0
            ? saved.keyID!
            : null,
        models: saved.models,
      };
    }
  } catch {
    // The preference can be unavailable in private browsing.
  }
  return { keyID: null, models: {} };
}

export function saveSelection(
  userID: number,
  keyID: number | null,
  modelID: string | null | undefined
) {
  const previous = readSelection(userID);
  if (keyID !== null && modelID !== undefined) {
    if (modelID === null) delete previous.models[keyID];
    else previous.models[keyID] = modelID;
  }
  try {
    localStorage.setItem(
      selectionStorageKey(userID),
      JSON.stringify({ ...previous, keyID })
    );
  } catch {
    // Keep the live selection when browser storage is unavailable.
  }
}

export async function fetchSub2API<T>(
  path: string,
  signal?: AbortSignal
): Promise<T> {
  const response = await fetch(`/api/sub2api/${path}`, {
    signal,
    cache: "no-store",
  });
  if (!response.ok) {
    throw new Error(`Sub2API catalog request failed (${response.status})`);
  }
  return response.json();
}

export async function fetchAppKeys(
  signal?: AbortSignal
): Promise<Sub2APIKey[]> {
  const keys = new Map<number, Sub2APIKey>();
  const pageSize = 50;
  for (let page = 1; ; page++) {
    const result = await fetchSub2API<{ total: number; items: Sub2APIKey[] }>(
      `keys?page=${page}&page_size=${pageSize}`,
      signal
    );
    for (const key of result.items) keys.set(key.id, key);
    if (page * pageSize >= result.total || result.items.length === 0) {
      return [...keys.values()];
    }
  }
}

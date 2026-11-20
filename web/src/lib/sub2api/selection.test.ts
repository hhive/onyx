/** @jest-environment jsdom */

import {
  fetchAppKeys,
  readSelection,
  saveSelection,
} from "@/lib/sub2api/selection";

afterEach(() => {
  localStorage.clear();
  jest.restoreAllMocks();
});

test("remembers each account's model for each key", () => {
  saveSelection(3, 42, "model-a");
  saveSelection(3, 61, "model-b");
  saveSelection(3, 42, undefined);
  saveSelection(4, 22, "model-c");
  expect(readSelection(3)).toEqual({
    keyID: 42,
    models: { 42: "model-a", 61: "model-b" },
  });
  expect(readSelection(4)).toEqual({ keyID: 22, models: { 22: "model-c" } });
  expect(readSelection(5)).toEqual({ keyID: null, models: {} });
});

test("fetches each page of the current user's key list", async () => {
  const first = Array.from({ length: 50 }, (_, i) => ({ id: i + 1 }));
  const fetchMock = jest
    .spyOn(global, "fetch")
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({ items: first, page: 1, page_size: 50, total: 51 })
      )
    )
    .mockResolvedValueOnce(
      new Response(
        JSON.stringify({
          items: [{ id: 51 }],
          page: 2,
          page_size: 50,
          total: 51,
        })
      )
    );
  const keys = await fetchAppKeys();
  expect(keys.map((key) => key.id)).toEqual([
    ...first.map((key) => key.id),
    51,
  ]);
  expect(fetchMock).toHaveBeenCalledTimes(2);
  expect(fetchMock.mock.calls[1]?.[0]).toBe(
    "/api/sub2api/keys?page=2&page_size=50"
  );
});

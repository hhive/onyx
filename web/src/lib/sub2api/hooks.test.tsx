/** @jest-environment jsdom */

import { act, renderHook, waitFor } from "@testing-library/react";
import { useSub2APISelection } from "@/lib/sub2api/hooks";
import { saveSelection } from "@/lib/sub2api/selection";

function json(value: unknown): Response {
  return new Response(JSON.stringify(value));
}

afterEach(() => {
  localStorage.clear();
  jest.restoreAllMocks();
});

test("restores scoped choices and ignores a catalog from a previous Key", async () => {
  saveSelection(970, 42, "model-a");
  let late: ((response: Response) => void) | undefined;
  let previousSignal: AbortSignal | null | undefined;
  jest.spyOn(global, "fetch").mockImplementation(async (path, options) => {
    switch (path) {
      case "/api/sub2api/session":
        return json({ user_id: 970, authorized: true });
      case "/api/sub2api/keys?page=1&page_size=50":
        return json({
          total: 2,
          items: [
            { id: 42, platform: "openai", selectable: true },
            { id: 67, platform: "anthropic", selectable: true },
          ],
        });
      case "/api/sub2api/keys/42/models":
        return json({ data: [{ id: "model-a" }] });
      case "/api/sub2api/keys/67/models":
        previousSignal = options?.signal;
        return new Promise<Response>((resolve) => {
          late = resolve;
        });
      default:
        throw new Error(String(path));
    }
  });

  const { result } = renderHook(() =>
    useSub2APISelection("onyx-user-for-restore-test")
  );
  await waitFor(() =>
    expect(result.current.selection).toEqual({
      key_id: 42,
      model_id: "model-a",
    })
  );
  act(() => result.current.selectKey("67"));
  await waitFor(() => expect(late).toBeDefined());
  expect(result.current.platform).toBe("anthropic");
  expect(result.current.selection).toBeNull();
  act(() => result.current.selectKey("42"));
  await waitFor(() => expect(previousSignal?.aborted).toBe(true));
  await act(async () => late?.(json({ data: [{ id: "model-b" }] })));
  await waitFor(() =>
    expect(result.current.selection).toEqual({
      key_id: 42,
      model_id: "model-a",
    })
  );
});

test("cancels unfinished key pages when the user signs out", async () => {
  let observed: AbortSignal | null | undefined;
  jest.spyOn(global, "fetch").mockImplementation(async (path, options) => {
    switch (path) {
      case "/api/sub2api/session":
        return json({ user_id: 971, authorized: true });
      case "/api/sub2api/keys?page=1&page_size=50":
        return json({ total: 51, items: [{ id: 1 }] });
      case "/api/sub2api/keys?page=2&page_size=50":
        observed = options?.signal;
        return new Promise<Response>(() => {});
      default:
        throw new Error(String(path));
    }
  });
  const initialProps: { user: string | undefined } = {
    user: "onyx-user-for-cancellation-test",
  };
  const { result, rerender } = renderHook(
    ({ user }) => useSub2APISelection(user),
    { initialProps }
  );
  await waitFor(() => expect(observed).toBeDefined());
  rerender({ user: undefined });
  expect(observed?.aborted).toBe(true);
  expect(result.current.keys).toEqual([]);
  expect(result.current.selection).toBeNull();
});

"use client";

import { useEffect, useState } from "react";
import useSWR from "swr";
import {
  fetchAppKeys,
  fetchSub2API,
  readSelection,
  saveSelection,
  type KeyModels,
  type Sub2APIKey,
  type Sub2APIModel,
  type Sub2APISelection,
  type Sub2APISession,
} from "@/lib/sub2api/selection";

export function useSub2APISelection(onyxUserID: string | undefined) {
  const session = useSWR(
    onyxUserID ? ["sub2api-session", onyxUserID] : null,
    () => fetchSub2API<Sub2APISession>("session"),
    { shouldRetryOnError: false }
  );
  const accountID = session.data?.user_id ?? null;
  const authorized = session.data?.authorized === true;
  const [keyDirectory, setKeyDirectory] = useState<{
    owner: string;
    accountID: number;
    keys?: Sub2APIKey[];
    failed?: boolean;
  }>();
  const [keyRevision, setKeyRevision] = useState(0);
  const currentDirectory =
    authorized &&
    keyDirectory?.owner === onyxUserID &&
    keyDirectory?.accountID === accountID
      ? keyDirectory
      : undefined;
  const keys = currentDirectory?.keys;
  const [choice, setChoice] = useState<{
    accountID: number;
    keyID: number | null;
    modelID: string;
    imageModelID: string;
  }>();
  const activeChoice =
    authorized && keys && choice?.accountID === accountID ? choice : undefined;
  const chosenKey = keys?.find(
    (key) => key.id === activeChoice?.keyID && key.selectable
  );
  const keyID = chosenKey?.id ?? null;
  const [catalog, setCatalog] = useState<{
    accountID: number;
    keyID: number;
    models?: Sub2APIModel[];
    imageModels?: Sub2APIModel[];
    failed?: boolean;
  }>();
  const [catalogRevision, setCatalogRevision] = useState(0);

  useEffect(() => {
    setKeyDirectory(undefined);
    setChoice(undefined);
    setCatalog(undefined);
    if (!onyxUserID || accountID === null || !authorized) return;
    const abort = new AbortController();
    void fetchAppKeys(abort.signal).then(
      (result) => {
        if (abort.signal.aborted) return;
        const saved = readSelection(accountID);
        const savedKey = result.find(
          (key) => key.id === saved.keyID && key.selectable
        );
        setChoice({
          accountID,
          keyID: savedKey?.id ?? null,
          modelID: savedKey ? (saved.models[savedKey.id] ?? "") : "",
          imageModelID: savedKey ? (saved.imageModels[savedKey.id] ?? "") : "",
        });
        setKeyDirectory({ owner: onyxUserID, accountID, keys: result });
      },
      () => {
        if (!abort.signal.aborted)
          setKeyDirectory({ owner: onyxUserID, accountID, failed: true });
      }
    );
    return () => abort.abort();
  }, [accountID, authorized, keyRevision, onyxUserID]);

  useEffect(() => {
    if (accountID === null || keyID === null || !authorized) return;
    const abort = new AbortController();
    setCatalog({ accountID, keyID });
    void fetchSub2API<KeyModels>(`keys/${keyID}/models`, abort.signal).then(
      (result) => {
        if (!abort.signal.aborted)
          setCatalog({
            accountID,
            keyID,
            models: result.data,
            imageModels: result.image_models,
          });
      },
      () => {
        if (!abort.signal.aborted)
          setCatalog({ accountID, keyID, failed: true });
      }
    );
    return () => abort.abort();
  }, [accountID, authorized, catalogRevision, keyID]);

  const matchingCatalog =
    authorized && catalog?.accountID === accountID && catalog?.keyID === keyID
      ? catalog
      : undefined;
  const models = matchingCatalog?.models ?? [];
  const modelID = models.some((model) => model.id === activeChoice?.modelID)
    ? activeChoice!.modelID
    : "";
  const imageModels = matchingCatalog?.imageModels ?? [];
  const imageModelID =
    imageModels.find(
      (model) =>
        model.confirmed !== false && model.id === activeChoice?.imageModelID
    )?.id ?? "";
  const selection: Sub2APISelection | null =
    authorized && keyID !== null && modelID
      ? {
          key_id: keyID,
          model_id: modelID,
        }
      : null;
  if (selection && imageModelID) selection.image_model_id = imageModelID;

  function selectKey(value: string) {
    if (accountID === null) return;
    const newKey = keys?.find(
      (key) => String(key.id) === value && key.selectable
    );
    const newKeyID = newKey?.id ?? null;
    if (newKeyID === keyID) return;
    const saved = readSelection(accountID);
    setCatalog(undefined);
    setChoice({
      accountID,
      keyID: newKeyID,
      modelID: newKeyID === null ? "" : (saved.models[newKeyID] ?? ""),
      imageModelID:
        newKeyID === null ? "" : (saved.imageModels[newKeyID] ?? ""),
    });
    saveSelection(accountID, newKeyID, undefined);
  }

  function selectModel(value: string) {
    if (!activeChoice || accountID === null || keyID === null) return;
    const chosenModel = models.find((model) => model.id === value);
    setChoice({ ...activeChoice, modelID: chosenModel?.id ?? "" });
    saveSelection(accountID, keyID, chosenModel?.id ?? null);
  }

  function selectImageModel(value: string) {
    if (!activeChoice || accountID === null || keyID === null) return;
    const chosenModel = imageModels.find(
      (model) => model.confirmed !== false && model.id === value
    );
    if (value && !chosenModel) return;
    setChoice({ ...activeChoice, imageModelID: chosenModel?.id ?? "" });
    saveSelection(accountID, keyID, undefined, chosenModel?.id ?? null);
  }

  return {
    accountID,
    sessionPending: Boolean(onyxUserID && !session.data),
    authorized,
    selection,
    keys: keys ?? [],
    keyID,
    platform: chosenKey?.platform,
    models,
    modelID,
    imageModels,
    imageModelID,
    selectImageModel,
    loading:
      session.isLoading ||
      (authorized && !keys && !currentDirectory?.failed) ||
      (keyID !== null && !matchingCatalog?.models && !matchingCatalog?.failed),
    error: Boolean(
      session.error || currentDirectory?.failed || matchingCatalog?.failed
    ),
    selectKey,
    selectModel,
    retry: () => {
      if (session.error) void session.mutate();
      else if (currentDirectory?.failed)
        setKeyRevision((revision) => revision + 1);
      else setCatalogRevision((revision) => revision + 1);
    },
  };
}

export type Sub2APISelectorState = ReturnType<typeof useSub2APISelection>;

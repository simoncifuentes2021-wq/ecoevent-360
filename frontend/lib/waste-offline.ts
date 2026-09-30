import type { PublicCollectionPoint, PublicWasteSubmission } from "@/types/waste";

const DB_NAME = "ecoevent-waste-public";
const DB_VERSION = 4;
export type QueuedWasteRecord = PublicWasteSubmission & { token: string; status: "PENDING" | "SYNCED" | "REJECTED"; synced_at?: string; error?: string; clear_after_sync?: boolean };

function openDb(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION);
    request.onupgradeneeded = () => {
      const db = request.result;
      if (!db.objectStoreNames.contains("forms")) db.createObjectStore("forms", { keyPath: "token" });
      if (!db.objectStoreNames.contains("records")) {
        const records = db.createObjectStore("records", { keyPath: "client_generated_id" });
        records.createIndex("token", "token", { unique: false });
      }
      // v1 keyed profiles by `token`, but profile reads and writes use the
      // event ID. Recreate only this small preference store with the right key.
      if (db.objectStoreNames.contains("profiles")) db.deleteObjectStore("profiles");
      if (db.objectStoreNames.contains("worker_profiles")) db.deleteObjectStore("worker_profiles");
      db.createObjectStore("profiles", { keyPath: "event_id" });
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function action<T>(storeName: string, mode: IDBTransactionMode, callback: (store: IDBObjectStore) => IDBRequest<T>): Promise<T> {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction(storeName, mode);
    const request = callback(transaction.objectStore(storeName));
    let result: T | undefined;
    request.onsuccess = () => { result = request.result; };
    transaction.oncomplete = () => { db.close(); resolve(result as T); };
    transaction.onerror = transaction.onabort = () => { db.close(); reject(transaction.error || request.error); };
  });
}

export const cachePublicForm = (token: string, form: PublicCollectionPoint) => action("forms", "readwrite", store => store.put({ ...form, token }));
export const readCachedPublicForm = (token: string) => action<(PublicCollectionPoint & { token: string }) | undefined>("forms", "readonly", store => store.get(token));
export const saveWorkerProfile = (eventId: string, profile: { name: string; rut: string }) => action("profiles", "readwrite", store => store.put({ ...profile, event_id: eventId }));
export const readWorkerProfile = (eventId: string) => action<{ name: string; rut: string; event_id: string } | undefined>("profiles", "readonly", store => store.get(eventId));
export const clearWorkerProfile = (eventId: string) => action<undefined>("profiles", "readwrite", store => store.delete(eventId));
export const savePendingRecord = (record: QueuedWasteRecord) => action("records", "readwrite", store => store.put(record));
export const deletePendingRecord = (clientGeneratedId: string) => action<undefined>("records", "readwrite", store => store.delete(clientGeneratedId));
export async function migrateLegacyCollectionQueue(token: string, form: PublicCollectionPoint): Promise<void> {
  const db = await openDb();
  await new Promise<void>((resolve, reject) => {
    const transaction = db.transaction(["forms", "records"], "readwrite");
    const formsRequest = transaction.objectStore("forms").getAll();
    const recordsRequest = transaction.objectStore("records").getAll();
    transaction.oncomplete = () => resolve();
    transaction.onerror = transaction.onabort = () => reject(transaction.error);
    let formsReady = false;
    let recordsReady = false;
    const migrate = () => {
      if (!formsReady || !recordsReady) return;
      const cachedForms = formsRequest.result as (PublicCollectionPoint & { token: string; code?: string; name?: string })[];
      const records = recordsRequest.result as (QueuedWasteRecord & { collection_point_id?: string })[];
      const legacyByToken = new Map(cachedForms.filter(item => item.event_id === form.event_id && item.token !== token).map(item => [item.token, item]));
      const store = transaction.objectStore("records");
      for (const record of records) {
        if (record.token === token || record.collection_point_id) continue;
        const legacy = legacyByToken.get(record.token);
        const point = legacy && form.collection_points.find(item => item.code === legacy.code || item.name === legacy.name);
        if (!point) continue;
        store.put({ ...record, token, collection_point_id: point.id });
      }
    };
    formsRequest.onsuccess = () => { formsReady = true; migrate(); };
    recordsRequest.onsuccess = () => { recordsReady = true; migrate(); };
  });
  db.close();
}
export const listTokenRecords = async (token: string): Promise<QueuedWasteRecord[]> => {
  const db = await openDb();
  return new Promise((resolve, reject) => {
    const transaction = db.transaction("records", "readonly");
    const request = transaction.objectStore("records").index("token").getAll(token);
    request.onsuccess = () => resolve((request.result as QueuedWasteRecord[]).sort((a, b) => b.recorded_at.localeCompare(a.recorded_at)));
    transaction.oncomplete = () => db.close();
    transaction.onerror = transaction.onabort = () => { db.close(); reject(transaction.error || request.error); };
  });
};

export function createUuid(): string {
  if (crypto.randomUUID) return crypto.randomUUID();
  return "xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx".replace(/[xy]/g, char => {
    const value = crypto.getRandomValues(new Uint8Array(1))[0] & 15;
    return (char === "x" ? value : (value & 3) | 8).toString(16);
  });
}

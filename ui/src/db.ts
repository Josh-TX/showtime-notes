class Database {
    private dbName: string;
    private storeName: string;

    constructor(dbName: string, storeName: string) {
        this.dbName = dbName;
        this.storeName = storeName;
    }

    private async getDB(): Promise<IDBDatabase> {
        return new Promise((resolve, reject) => {
            const request = indexedDB.open(this.dbName, 1);

            request.onupgradeneeded = (event: IDBVersionChangeEvent) => {
                const db = request.result;
                if (!db.objectStoreNames.contains(this.storeName)) {
                    db.createObjectStore(this.storeName, { keyPath: 'id' });
                }
            };

            request.onsuccess = () => resolve(request.result);
            request.onerror = () => reject(request.error);
        });
    }

    async set(key: string, blob: Blob): Promise<void> {
        const db = await this.getDB();

        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readwrite');
            const store = transaction.objectStore(this.storeName);

            const request = store.put({ id: key, blob });
            request.onsuccess = () => resolve();
            request.onerror = () => reject(request.error);
        });
    }

    async get(key: string): Promise<Blob> {
        const db = await this.getDB();

        return new Promise((resolve, reject) => {
            const transaction = db.transaction(this.storeName, 'readonly');
            const store = transaction.objectStore(this.storeName);

            const request = store.get(key);
            request.onsuccess = () => {
                const result = request.result;
                if (result && result.blob) {
                    resolve(result.blob as Blob);
                } else {
                    reject(new Error(`No blob found for key: ${key}`));
                }
            };
            request.onerror = () => reject(request.error);
        });
    }
}
export var db = new Database("main", "songs");
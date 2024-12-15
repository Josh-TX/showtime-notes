//this code runs in the main thread

import { workerPool } from "./worker-pool";

export var workerOperations = {
    async getSpectrogram(input: number): Promise<number[][]> {
        return workerPool.runOperation("getSpectrogram", input);
    }
}
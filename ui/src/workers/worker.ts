//this code runs in a web worker

import type { WorkerInputWrapper, WorkerOutputWrapper, WorkerOutputData, AllWorkerOperations } from "./worker-models";


var operations: AllWorkerOperations = {
    async getSpectrogram(input: number): Promise<number[][]> {
        new Date().getTime();
        console.log("getSpectrogram", input)
        return [];
    },

    async somethingDifferent(input: string): Promise<string> {
        new Date().getTime();
        return "hi";
    }
}

self.addEventListener('message', (event) => {
    var workerInput = event.data as WorkerInputWrapper;
    runOperation(workerInput).then(res => {
        var workerOutput: WorkerOutputWrapper = {
            id: workerInput.id,
            data: res
        }
        self.postMessage(workerOutput);
    });
});

function runOperation(input: WorkerInputWrapper): Promise<WorkerOutputData> {
    //for some reason Promise<any> doesn't work
    var operation: any = operations[input.name];
    return operation(input.data);
}
//this file should only contain type definitions, since it'll be used both the main thread and each worker

//import { GetWeightsRequest, ChartData, DayLogAFR, GetLogAfrsRequest, DayPrice, DayReturn } from "./models"

export type WorkerInputWrapper = {
    id: string,
    name: OperationName,
    data: WorkerInputData
}
export type WorkerProgress = {
    id: string,
    progress: number
}
export type WorkerOutputWrapper = {
    id: string,
    data: WorkerOutputData
}
export type WorkerInputData = any;
export type WorkerOutputData = any

export interface AllWorkerOperations {
    getSpectrogram(input: number): Promise<number[][]>
    somethingDifferent(input: string): Promise<string> 
}

export type OperationName = keyof AllWorkerOperations
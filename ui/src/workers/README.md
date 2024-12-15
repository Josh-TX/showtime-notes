# Workers

I have my own implementation of workers that attempts to support these 3 goals:

* Reuse worker from a pool
* Support different operations
* Strongly typed inputs & outputs

There may exist a package that fulfills these goals, but I don't know of any

## How it works

The key that binds everything together is the `AllWorkerOperations` interface. Each unique operation should be a function on this interface. The main thread has `workerOperations` instance defined in `worker-caller.ts` that implements this interface. And `worker.ts` also implements this interface. Since both places reference the same interface, there's no risk of a type mismatch. 

The worker-caller calls `workerPool.runOperation()`, which finds an available worker and sends a message for the worker to pick up. Workers just have a single "message" event listener, so in order to run the correct operation amongst several, the message contains an `operationName` that should match a function name on the `AllWorkerOperations` interface. The message also contains an unique id that allows the `workerPool` to resolve the correct promise when it completes.

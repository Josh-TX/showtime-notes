import { HubConnectionBuilder, HubConnection } from "@microsoft/signalr";
class SignalRService {
    count = $state(0);
    private connection: HubConnection;
    constructor() {
        this.connection = new HubConnectionBuilder()
            .withUrl("main-hub")
            .withAutomaticReconnect()
            //.configureLogging(LogLevel.Debug)
            .build();
        this.connection
            .start()
            .then(() => console.log("Connected to SignalR hub"))
            .catch((err) => console.error("SignalR connection error:", err));
        this.connection.on("count", (newCount: number) => {
            this.count = newCount;
        });
    }

    public add(number: number) {
        this.connection.invoke("Add", number);
    }
}
export var signalRService = new SignalRService();

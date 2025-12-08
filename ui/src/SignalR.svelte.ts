import { HubConnectionBuilder, HubConnection } from "@microsoft/signalr";
class SignalRService {
    otherUserInfos = $state<UserInfo[]>(null);
    myUserInfo = $state<UserInfo | null>(null);
    syncedToDisplayName = $state<string | null>(null);
    sceneInfos = $state<SceneInfo[] | null>(null);
    selectedSceneId = $state<string | null>(null);
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

        this.connection.on("UserInfos", (userInfos: UserInfo[]) => {
            console.log("userInfos", userInfos);
            this.myUserInfo = userInfos.find((z) => z.connectionId == this.connection.connectionId);
            this.otherUserInfos = userInfos.filter((z) => z.connectionId != this.connection.connectionId);
            this.handleSync();
        });
        this.connection.on("SceneInfos", (sceneInfos: SceneInfo[]) => {
            this.sceneInfos = sceneInfos;
            if (this.sceneInfos.length && (this.selectedSceneId == null || this.sceneInfos.every((z) => z.id != this.selectedSceneId))) {
                this.selectScene(this.sceneInfos[0].id);
            }
        });
    }

    sync(UserInfo: UserInfo) {
        this.syncedToDisplayName = UserInfo.displayName;
        this.handleSync();
    }

    addScene(name: string) {
        var newSceneInfo: SceneInfo = {
            id: generateId(),
            name: name,
            notes: "",
            duration: 60,
            cards: [],
        };
        this.connection.invoke("AddScene", newSceneInfo);
        this.sceneInfos.push(newSceneInfo);
        //we don't want to instantly select the scene, since we need to ensure SceneInfos fires before UserInfos
        setTimeout(() => {
            this.selectScene(newSceneInfo.id);
        }, 50);
    }

    selectScene(sceneId: string) {
        if (this.selectedSceneId != sceneId) {
            this.selectedSceneId = sceneId;
            var userState: UserState = {
                sceneId: sceneId,
                position: 0,
                asOfDate: null,
            };
            this.myUserInfo.state = userState;
            this.connection.invoke("UpdateUserState", userState);
        }
    }

    private handleSync() {
        var syncedOtherUserInfo = this.otherUserInfos.find((z) => z.displayName == this.syncedToDisplayName);
        if (syncedOtherUserInfo && syncedOtherUserInfo.state) {
            this.selectScene(syncedOtherUserInfo.state.sceneId);
        }
    }
}
export var signalRService = new SignalRService();

type SceneInfo = {
    id: string;
    name: string;
    notes: string;
    duration: number;
    cards: Card[];
};

type UserInfo = {
    name: string;
    displayName: string;
    connectionId: string;
    sceneId: string | null;
    state: UserState | null;
};

type UserState = {
    sceneId: string;
    asOfDate: number | null;
    position: number;
};

type Card = {
    time: number;
    text: string | null;
};

function generateId(): string {
    return Math.random().toString(36).substring(2, 5) + Date.now().toString(36).slice(-5);
}

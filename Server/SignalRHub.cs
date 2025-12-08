using System.Collections.Concurrent;
using Microsoft.AspNetCore.SignalR;

public class SignalRHub(
    ActiveUserService _activeUserService,
    SceneService _sceneService
    ) : Hub
{
    private static int _count = 0;
    private static class EventNames
    {
        public const string UserInfos = "UserInfos";
        public const string SceneInfos = "SceneInfos";
    };

    public override async Task OnConnectedAsync()
    {
        var name = Context.User?.Identity?.Name ?? "unknown_user";
        await _activeUserService.AddUser(name, Context.ConnectionId);
        await Clients.All.SendAsync(EventNames.UserInfos, _activeUserService.GetUsers());
        await Clients.All.SendAsync(EventNames.SceneInfos, _sceneService.GetScenes());
    }

    public override Task OnDisconnectedAsync(Exception? exception)
    {
        _activeUserService.RemoveUser(Context.ConnectionId);
        return base.OnDisconnectedAsync(exception);
    }

    public async Task UpdateUserState(UserState userState)
    {
        _activeUserService.UpdateUserState(Context.ConnectionId, userState);
        await Clients.All.SendAsync(EventNames.UserInfos, _activeUserService.GetUsers());
    }


    public async Task AddScene(SceneInfo sceneInfo)
    {
        await _sceneService.AddScene(sceneInfo);
        await Clients.All.SendAsync(EventNames.SceneInfos, _sceneService.GetScenes());
    }
}



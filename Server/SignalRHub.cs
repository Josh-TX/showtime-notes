using Microsoft.AspNetCore.SignalR;

public class SignalRHub(ILogger<SignalRHub> _logger) : Hub
{
    private static int _count = 0;
    public override async Task OnConnectedAsync()
    {
        await Clients.Caller.SendAsync("count", _count);
    }
    public override Task OnDisconnectedAsync(Exception? exception)
    {
        return base.OnDisconnectedAsync(exception);
    }

    public async Task Add(int? amount)
    {
        _count += 1;
        await Clients.All.SendAsync("count", _count);
    }
}
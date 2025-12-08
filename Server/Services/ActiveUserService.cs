using System.Collections.Concurrent;
using System.Threading;

public class ActiveUserService
{
    private readonly SemaphoreSlim _lock = new(1, 1);
    private readonly ConcurrentDictionary<string, ActiveUser> _activeUsers = new();

    public IEnumerable<ActiveUser> GetUsers() => _activeUsers.Values;

    public async Task<ActiveUser> AddUser(string name, string connectionId)
    {
        //even though the concurrentDictionary is thread-safe, the process of checking for name indexes can't run concurrently
        await _lock.WaitAsync();
        try
        {
            var sameUserNames = _activeUsers.Values.Where(z => z.Name == name).ToList();
            int index = !sameUserNames.Any() ? 1 : Enumerable.Range(1, 999).First(i => !sameUserNames.Select(z => z.Index).Contains(i));
            var displayName = index == 1 ? name : $"{name} ({index})";
            var user = new ActiveUser
            {
                Name = name,
                Index = index,
                DisplayName = displayName,
                ConnectionId = connectionId
            };
            _activeUsers[connectionId] = user;
            return user;
        }
        finally
        {
            _lock.Release();
        }
    }

    public void RemoveUser(string connectionId)
    {
        _activeUsers.TryRemove(connectionId, out _);
    }

    public void UpdateUserState(string connectionId, UserState userState)
    {
        _activeUsers.TryGetValue(connectionId, out var activeUser);
        if (activeUser != null)
        {
            activeUser.State = userState;
        }
    }
}

public class ActiveUser
{
    public required string Name { get; init; }
    public required int Index { get; init; }
    public required string DisplayName { get; init; }
    public required string ConnectionId { get; init; }
    public UserState? State { get; set; }
}

public class UserState
{
    public required string SceneId { get; set; }

    //when null, indicates it's not currently playing
    public long? AsOfDate { get; set; }
    public int Position { get; set; }

}
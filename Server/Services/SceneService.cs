using System.Collections.Concurrent;
using System.Threading;

public class SceneService
{
    public SceneService()
    {
        _scenes = LoadFromDisk();
    }
    private readonly SemaphoreSlim _lock = new(1, 1);
    private readonly List<SceneInfo> _scenes = new();
    private readonly string _storagePath = Path.Combine("scenes.json");
    public IEnumerable<SceneInfo> GetScenes() => _scenes.AsEnumerable();

    public async Task AddScene(SceneInfo sceneInfo)
    {
        await _lock.WaitAsync();
        try
        {
            _scenes.Add(sceneInfo);
        }
        finally
        {
            _lock.Release();
        }
        SaveToDisk();
    }

    public async Task RemoveScene(string id)
    {
        await _lock.WaitAsync();
        try
        {
            _scenes.RemoveAll(z => z.Id == id);
        }
        finally
        {
            _lock.Release();
        }
        SaveToDisk();
    }

    private void SaveToDisk()
    {
        var json = System.Text.Json.JsonSerializer.Serialize(_scenes);
        File.WriteAllText(_storagePath, json);
    }

    private List<SceneInfo> LoadFromDisk()
    {
        if (!File.Exists(_storagePath))
        {
            return [];
        }
        var json = File.ReadAllText(_storagePath);
        var scenes = System.Text.Json.JsonSerializer.Deserialize<List<SceneInfo>>(json);
        ArgumentNullException.ThrowIfNull(scenes);
        return scenes;
    }
}

public class SceneInfo
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public required string Notes { get; set; }
    public required int Duration { get; set; }
    public required IEnumerable<Card> Cards { get; set; }

}

public class Card
{
    public required string Time { get; init; }
    public required string Name { get; init; }
}
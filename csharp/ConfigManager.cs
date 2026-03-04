using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using System.Text.Json.Serialization;

namespace FileRename;

public class RowConfig
{
    [JsonPropertyName("source_path")]     public string SourcePath      { get; set; } = "";
    [JsonPropertyName("dest_path")]       public string DestPath        { get; set; } = "";
    [JsonPropertyName("base_name")]       public string BaseName        { get; set; } = "";
    [JsonPropertyName("year")]            public string Year            { get; set; } = DateTime.Now.Year.ToString();
    [JsonPropertyName("month")]           public string Month           { get; set; } = DateTime.Now.Month.ToString("D2");
    [JsonPropertyName("day")]             public string Day             { get; set; } = DateTime.Now.Day.ToString("D2");
    [JsonPropertyName("use_year")]        public bool   UseYear         { get; set; } = true;
    [JsonPropertyName("use_month")]       public bool   UseMonth        { get; set; } = true;
    [JsonPropertyName("use_day")]         public bool   UseDay          { get; set; } = false;
    [JsonPropertyName("use_underscores")] public bool   UseUnderscores  { get; set; } = true;
    [JsonPropertyName("selected_file_path")] public string SelectedFilePath { get; set; } = "";
}

public static class ConfigManager
{
    private static string ConfigFile =>
        Path.Combine(AppContext.BaseDirectory, "config.json");

    private static Dictionary<string, RowConfig>? _cache;

    private static readonly JsonSerializerOptions Opts = new()
    {
        WriteIndented = true,
        PropertyNameCaseInsensitive = true,
    };

    public static Dictionary<string, RowConfig> Load()
    {
        if (_cache != null) return _cache;
        if (!File.Exists(ConfigFile)) { _cache = []; return _cache; }
        try
        {
            _cache = JsonSerializer.Deserialize<Dictionary<string, RowConfig>>(
                File.ReadAllText(ConfigFile), Opts) ?? [];
        }
        catch { _cache = []; }
        return _cache;
    }

    public static void Save(Dictionary<string, RowConfig> config)
    {
        _cache = config;
        File.WriteAllText(ConfigFile, JsonSerializer.Serialize(config, Opts));
    }

    public static List<int> GetRowIndices() =>
        Load().Keys
              .Where(k => k.StartsWith("row") && int.TryParse(k[3..], out _))
              .Select(k => int.Parse(k[3..]))
              .OrderBy(i => i)
              .ToList();

    public static RowConfig GetRow(int index) =>
        Load().TryGetValue($"row{index}", out var r) ? r : new RowConfig();

    public static void SetRow(int index, RowConfig row)
    {
        var c = Load(); c[$"row{index}"] = row; Save(c);
    }

    public static void DeleteRow(int index)
    {
        var c = Load(); c.Remove($"row{index}"); Save(c);
    }

    public static void AddRow(int index)
    {
        var c = Load();
        if (!c.ContainsKey($"row{index}")) { c[$"row{index}"] = new RowConfig(); Save(c); }
    }

    public static void Normalize()
    {
        var rows = Load()
            .Where(kv => kv.Key.StartsWith("row") && int.TryParse(kv.Key[3..], out _))
            .OrderBy(kv => int.Parse(kv.Key[3..]))
            .Select(kv => kv.Value)
            .ToList();
        var nc = new Dictionary<string, RowConfig>();
        for (int i = 0; i < rows.Count; i++) nc[$"row{i}"] = rows[i];
        _cache = null;
        Save(nc);
    }

    public static void EnsureInitial(int count = 3)
    {
        if (File.Exists(ConfigFile)) return;
        var c = new Dictionary<string, RowConfig>();
        for (int i = 0; i < count; i++) c[$"row{i}"] = new RowConfig();
        Save(c);
    }
}

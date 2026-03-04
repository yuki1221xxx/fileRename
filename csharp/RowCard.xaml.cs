using System;
using System.IO;
using System.Linq;
using System.Windows;
using System.Windows.Controls;
using System.Windows.Media;
using System.Windows.Threading;
using Microsoft.Win32;

namespace FileRename;

public partial class RowCard : UserControl
{
    public int RowIndex { get; }
    public event Action<int>? DeleteRequested;

    private RowConfig _cfg;
    private FileSystemWatcher? _watcher;
    private DispatcherTimer? _statusTimer;
    private bool _loading;   // フラグ: ロード中はイベント無視

    public RowCard(int rowIndex)
    {
        RowIndex = rowIndex;
        _cfg = ConfigManager.GetRow(rowIndex);
        InitializeComponent();
        RowHeader.Text = $"行 {rowIndex + 1}";
        InitCombos();
        _loading = true;
        LoadState();
        _loading = false;
        UpdatePreview();
    }

    // ── コンボ初期化 ──────────────────────────────────────────
    private void InitCombos()
    {
        var now = DateTime.Now;
        YearCombo.ItemsSource  = Enumerable.Range(now.Year - 5, 11).Select(y => y.ToString()).ToList();
        MonthCombo.ItemsSource = Enumerable.Range(1, 12).Select(m => m.ToString("D2")).ToList();
        DayCombo.ItemsSource   = Enumerable.Range(1, 31).Select(d => d.ToString("D2")).ToList();
    }

    // ── 設定から画面を復元 ──────────────────────────────────────
    private void LoadState()
    {
        SourcePathBox.Text = _cfg.SourcePath;
        DestPathBox.Text   = _cfg.DestPath;
        BaseNameBox.Text   = _cfg.BaseName;

        UseYearChk.IsChecked       = _cfg.UseYear;
        UseMonthChk.IsChecked      = _cfg.UseMonth;
        UseDayChk.IsChecked        = _cfg.UseDay;
        UseUnderscoreChk.IsChecked = _cfg.UseUnderscores;

        YearCombo.SelectedItem  = _cfg.Year;
        MonthCombo.SelectedItem = _cfg.Month;
        DayCombo.SelectedItem   = _cfg.Day;

        if (Directory.Exists(_cfg.SourcePath))
        {
            RefreshFileList();
            StartWatcher(_cfg.SourcePath);
        }
    }

    // ── ファイルリスト更新 ────────────────────────────────────
    private void RefreshFileList()
    {
        var folder = _cfg.SourcePath;
        if (!Directory.Exists(folder)) return;
        try
        {
            var files = Directory.GetFiles(folder)
                                 .Select(Path.GetFileName)
                                 .OfType<string>()
                                 .OrderBy(f => f)
                                 .ToList();
            Dispatcher.InvokeAsync(() =>
            {
                var sel = FileListBox.SelectedItem?.ToString();
                FileListBox.ItemsSource = files;
                if (sel != null && files.Contains(sel))
                    FileListBox.SelectedItem = sel;
            });
        }
        catch { /* アクセス不可なら無視 */ }
    }

    private void StartWatcher(string folder)
    {
        _watcher?.Dispose();
        if (!Directory.Exists(folder)) return;
        try
        {
            _watcher = new FileSystemWatcher(folder)
            {
                NotifyFilter = NotifyFilters.FileName,
                EnableRaisingEvents = true,
            };
            _watcher.Created += (_, _) => RefreshFileList();
            _watcher.Deleted += (_, _) => RefreshFileList();
            _watcher.Renamed += (_, _) => RefreshFileList();
        }
        catch { /* 監視できないフォルダは無視 */ }
    }

    // ── フォルダ選択 ──────────────────────────────────────────
    private void SourceSelectBtn_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "走査元フォルダを選択" };
        if (dlg.ShowDialog() != true) return;
        _cfg.SourcePath = dlg.FolderName;
        SourcePathBox.Text = _cfg.SourcePath;
        ConfigManager.SetRow(RowIndex, _cfg);
        RefreshFileList();
        StartWatcher(_cfg.SourcePath);
    }

    private void DestSelectBtn_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "移動先フォルダを選択" };
        if (dlg.ShowDialog() != true) return;
        _cfg.DestPath = dlg.FolderName;
        DestPathBox.Text = _cfg.DestPath;
        ConfigManager.SetRow(RowIndex, _cfg);
    }

    // ── ファイル選択 ──────────────────────────────────────────
    private void FileListBox_SelectionChanged(object s, SelectionChangedEventArgs e)
    {
        if (FileListBox.SelectedItem is not string fname) return;
        var full = Path.Combine(_cfg.SourcePath, fname);
        _cfg.SelectedFilePath = full;
        try
        {
            var fi  = new FileInfo(full);
            var ext = fi.Extension.Length > 0 ? fi.Extension : "(拡張子なし)";
            FileInfoText.Text       = $"{fname}\n{ext}  ·  {fi.Length:N0} bytes\n{fi.LastWriteTime:yyyy-MM-dd HH:mm}";
            FileInfoText.Foreground = new SolidColorBrush(Color.FromRgb(52, 58, 64));
        }
        catch { FileInfoText.Text = fname; }
        ConfigManager.SetRow(RowIndex, _cfg);
        UpdatePreview();
    }

    // ── リネーム設定変更 ──────────────────────────────────────
    private void BaseNameBox_TextChanged(object s, TextChangedEventArgs e)
    {
        if (_loading) return;
        _cfg.BaseName = BaseNameBox.Text;
        ConfigManager.SetRow(RowIndex, _cfg);
        UpdatePreview();
    }

    private void DateOpt_Changed(object s, RoutedEventArgs e)
    {
        if (_loading) return;
        _cfg.UseYear        = UseYearChk.IsChecked  == true;
        _cfg.UseMonth       = UseMonthChk.IsChecked == true;
        _cfg.UseDay         = UseDayChk.IsChecked   == true;
        _cfg.UseUnderscores = UseUnderscoreChk.IsChecked == true;
        ConfigManager.SetRow(RowIndex, _cfg);
        UpdatePreview();
    }

    private void DateCombo_Changed(object s, SelectionChangedEventArgs e)
    {
        if (_loading) return;
        _cfg.Year  = YearCombo.SelectedItem?.ToString()  ?? DateTime.Now.Year.ToString();
        _cfg.Month = MonthCombo.SelectedItem?.ToString() ?? DateTime.Now.Month.ToString("D2");
        _cfg.Day   = DayCombo.SelectedItem?.ToString()   ?? DateTime.Now.Day.ToString("D2");
        ConfigManager.SetRow(RowIndex, _cfg);
        UpdatePreview();
    }

    // ── プレビュー更新 ────────────────────────────────────────
    private void UpdatePreview()
    {
        var sep   = _cfg.UseUnderscores ? "_" : "";
        var parts = new System.Collections.Generic.List<string>();
        if (_cfg.UseYear)  parts.Add(_cfg.Year);
        if (_cfg.UseMonth) parts.Add(_cfg.Month);
        if (_cfg.UseDay)   parts.Add(_cfg.Day);

        var name = _cfg.BaseName;
        if (parts.Count > 0)
        {
            var dp = string.Join(sep, parts);
            name = name.Length > 0 ? $"{name}{sep}{dp}" : dp;
        }

        var ext  = string.IsNullOrEmpty(_cfg.SelectedFilePath)
                   ? "" : Path.GetExtension(_cfg.SelectedFilePath);
        PreviewText.Text = (name.Length > 0 || ext.Length > 0)
                           ? $"{name}{ext}"
                           : "（ベース名を入力してください）";
    }

    // ── 実行 ─────────────────────────────────────────────────
    private void ExecuteBtn_Click(object s, RoutedEventArgs e)
    {
        if (string.IsNullOrEmpty(_cfg.SelectedFilePath) || !File.Exists(_cfg.SelectedFilePath))
        { ShowStatus("⚠ ファイル未選択", "#DC3545"); return; }

        if (string.IsNullOrEmpty(_cfg.DestPath))
        { ShowStatus("⚠ 移動先未選択", "#DC3545"); return; }

        var newName = PreviewText.Text;
        if (newName == "（ベース名を入力してください）")
        { ShowStatus("⚠ ベース名を入力してください", "#DC3545"); return; }

        var dest = Path.Combine(_cfg.DestPath, newName);
        try
        {
            if (File.Exists(dest))
            {
                var r = MessageBox.Show($"{newName} は既に存在します。上書きしますか？",
                                        "確認", MessageBoxButton.YesNo, MessageBoxImage.Question);
                if (r != MessageBoxResult.Yes) return;
            }
            Directory.CreateDirectory(_cfg.DestPath);
            File.Move(_cfg.SelectedFilePath, dest, overwrite: true);

            _cfg.SelectedFilePath = "";
            ConfigManager.SetRow(RowIndex, _cfg);
            FileListBox.SelectedItem = null;
            FileInfoText.Text        = "ファイルを選択してください";
            FileInfoText.Foreground  = new SolidColorBrush(Color.FromRgb(108, 117, 125));
            RefreshFileList();
            ShowStatus("✔ 実行完了", "#198754");
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
        }
    }

    // ── 削除 ─────────────────────────────────────────────────
    private void DeleteBtn_Click(object s, RoutedEventArgs e) =>
        DeleteRequested?.Invoke(RowIndex);

    // ── ステータス表示（3秒で消える） ────────────────────────
    private void ShowStatus(string msg, string hex)
    {
        StatusText.Text       = msg;
        StatusText.Foreground = new SolidColorBrush(
            (Color)ColorConverter.ConvertFromString(hex));

        _statusTimer?.Stop();
        _statusTimer = new DispatcherTimer { Interval = TimeSpan.FromSeconds(3) };
        _statusTimer.Tick += (_, _) => { StatusText.Text = ""; _statusTimer!.Stop(); };
        _statusTimer.Start();
    }

    // ── クリーンアップ ────────────────────────────────────────
    public void Cleanup()
    {
        _watcher?.Dispose();
        _statusTimer?.Stop();
    }
}

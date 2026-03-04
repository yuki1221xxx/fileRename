using System;
using System.IO;
using System.IO.Compression;
using System.Linq;
using System.Windows;
using System.Windows.Media;
using Microsoft.Win32;

namespace FileRename;

public partial class MainWindow : Window
{
    public MainWindow()
    {
        ConfigManager.EnsureInitial(3);
        ConfigManager.Normalize();
        InitializeComponent();
        BuildRows();
    }

    // ── 行の構築 ──────────────────────────────────────────────
    private void BuildRows()
    {
        foreach (RowCard card in RowsPanel.Children.OfType<RowCard>())
            card.Cleanup();
        RowsPanel.Children.Clear();

        foreach (var idx in ConfigManager.GetRowIndices())
        {
            var card = new RowCard(idx);
            card.DeleteRequested += HandleDelete;
            RowsPanel.Children.Add(card);
        }
    }

    private void HandleDelete(int idx)
    {
        ConfigManager.DeleteRow(idx);
        ConfigManager.Normalize();
        BuildRows();
    }

    private void AddRowBtn_Click(object s, RoutedEventArgs e)
    {
        ConfigManager.Normalize();
        ConfigManager.AddRow(ConfigManager.GetRowIndices().Count);
        BuildRows();
    }

    // ── ZIP化タブ ─────────────────────────────────────────────
    private void ZipSrcBtn_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "対象フォルダを選択" };
        if (dlg.ShowDialog() != true) return;
        ZipSrcBox.Text = dlg.FolderName;
        if (string.IsNullOrEmpty(ZipDestBox.Text))
            ZipDestBox.Text = Path.GetDirectoryName(dlg.FolderName) ?? "";
        if (string.IsNullOrEmpty(ZipNameBox.Text))
            ZipNameBox.Text = Path.GetFileName(dlg.FolderName);
    }

    private void ZipDestBtn_Click(object s, RoutedEventArgs e)
    {
        var dlg = new OpenFolderDialog { Title = "保存先フォルダを選択" };
        if (dlg.ShowDialog() == true) ZipDestBox.Text = dlg.FolderName;
    }

    private void ZipBtn_Click(object s, RoutedEventArgs e)
    {
        var src  = ZipSrcBox.Text;
        var dest = ZipDestBox.Text;
        var name = ZipNameBox.Text.Trim();

        if (string.IsNullOrEmpty(src) || !Directory.Exists(src))
        { SetZipStatus("⚠ フォルダが選択されていません", "#DC3545"); return; }
        if (string.IsNullOrEmpty(dest))
        { SetZipStatus("⚠ 保存先フォルダを指定してください", "#DC3545"); return; }
        if (string.IsNullOrEmpty(name))
        { SetZipStatus("⚠ ZIP名を入力してください", "#DC3545"); return; }

        Directory.CreateDirectory(dest);
        var stem = name.EndsWith(".zip", StringComparison.OrdinalIgnoreCase) ? name[..^4] : name;
        var outPath = Path.Combine(dest, $"{stem}.zip");
        try
        {
            if (File.Exists(outPath)) File.Delete(outPath);
            ZipFile.CreateFromDirectory(src, outPath);
            SetZipStatus($"✅ 完了: {Path.GetFileName(outPath)}", "#198754");
        }
        catch (Exception ex)
        {
            MessageBox.Show(ex.Message, "エラー", MessageBoxButton.OK, MessageBoxImage.Error);
            SetZipStatus("⚠ 失敗しました", "#DC3545");
        }
    }

    private void SetZipStatus(string msg, string hex)
    {
        ZipStatusText.Text       = msg;
        ZipStatusText.Foreground = new SolidColorBrush(
            (Color)ColorConverter.ConvertFromString(hex));
    }
}

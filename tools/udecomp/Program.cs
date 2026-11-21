// Dekompiliert alle Klassen eines Unreal-Pakets (.u) nach UnrealScript (.uc).
// Aufruf: dotnet run -- <paket.u> <ausgabeordner> [klassenfilter]
using System.Text;
using UELib;
using UELib.Core;

if (args.Length < 2)
{
    Console.WriteLine("Aufruf: udecomp <paket.u> <ausgabeordner> [klassenfilter]");
    return 1;
}

if (args[0] == "--exports")
{
    // Alle Exporte mit Klasse, Datei-Offset und Groesse als TSV ausgeben
    var p = UnrealLoader.LoadPackage(args[1], FileAccess.Read);
    // Nur die Tabellen lesen (LoadPackage tut das bereits), keine Objekte konstruieren
    foreach (var e in p.Exports)
    {
        string cls = "?";
        try { cls = e.ClassIndex == 0 ? "Class" : p.GetIndexObjectName(e.ClassIndex); } catch { }
        Console.WriteLine($"{e.ObjectName}\t{cls}\t{e.SerialOffset}\t{e.SerialSize}");
    }
    return 0;
}

if (args[0] == "--tokens")
{
    // Bytecode-Tokens einer Funktion: Speicher-/Plattenposition und Groesse
    // Aufruf: --tokens <paket> <Klassenname> <Funktionsname>
    var p = UnrealLoader.LoadPackage(args[1], FileAccess.Read);
    p.InitializePackage();
    // Klassenname oder "Klasse.State" fuer Funktionen innerhalb eines States
    var outerParts = args[2].Split('.');
    var fn = p.Objects.OfType<UFunction>().First(f => f.Name.ToString() == args[3]
                                                    && f.Outer?.Name.ToString() == outerParts[^1]
                                                    && (outerParts.Length == 1
                                                        || f.Outer?.Outer?.Name.ToString() == outerParts[0]));
    fn.BeginDeserializing();
    Console.WriteLine($"Export {fn.ExportTable.Index + 1}  Offset {fn.ExportTable.SerialOffset}");
    var mgr = fn.ByteCodeManager;
    mgr.Deserialize();
    foreach (var t in mgr.DeserializedTokens)
        Console.WriteLine($"{t.Position:X4}\t{t.StoragePosition:X4}\t{t.Size}\t{t.StorageSize}\t{t.GetType().Name}");
    return 0;
}

if (args[0] == "--names")
{
    // Namenstabelle: Index fuer EX_VirtualFunction / Namenskonstanten
    var p = UnrealLoader.LoadPackage(args[1], FileAccess.Read);
    for (int i = 0; i < p.Names.Count; i++)
        Console.WriteLine($"{i}\t{p.Names[i]}");
    return 0;
}

if (args[0] == "--imports")
{
    // Import-Tabelle: Objektreferenz im Bytecode ist -(Index+1)
    var p = UnrealLoader.LoadPackage(args[1], FileAccess.Read);
    for (int i = 0; i < p.Imports.Count; i++)
    {
        var im = p.Imports[i];
        string outer = "";
        try { outer = im.OuterIndex == 0 ? "" : p.GetIndexObjectName(im.OuterIndex); } catch { }
        Console.WriteLine($"{-(i + 1)}\t{im.ObjectName}\t{im.ClassName}\t{outer}");
    }
    for (int i = 0; i < p.Exports.Count; i++)
    {
        var ex = p.Exports[i];
        string outer = "";
        try { outer = ex.OuterIndex == 0 ? "" : p.GetIndexObjectName(ex.OuterIndex); } catch { }
        Console.WriteLine($"{i + 1}\t{ex.ObjectName}\texport\t{outer}");
    }
    return 0;
}

string path = args[0], outDir = args[1];
string? filter = args.Length > 2 ? args[2] : null;
Directory.CreateDirectory(outDir);

var pkg = UnrealLoader.LoadPackage(path, FileAccess.Read);
Console.WriteLine($"Paket {pkg.PackageName}: Version {pkg.Version}, Lizenz {pkg.LicenseeVersion}, Build {pkg.Build}");
pkg.InitializePackage();

// Alle TextBuffer-Objekte (z. B. Cutscene-Skripte in Maps) als .txt ausgeben
foreach (var tb in pkg.Objects.OfType<UTextBuffer>().Where(t => t.ExportTable != null))
{
    try
    {
        tb.BeginDeserializing();
        string outer = tb.Outer?.Name.ToString() ?? "root";
        string file = Path.Combine(outDir, $"{outer}.{tb.Name}.txt");
        File.WriteAllText(file, tb.ScriptText ?? "", Encoding.UTF8);
    }
    catch (Exception ex)
    {
        Console.WriteLine($"TextBuffer {tb.Name}: {ex.Message}");
    }
}

int ok = 0, fail = 0;
foreach (var obj in pkg.Objects.OfType<UClass>().Where(c => c.ExportTable != null))
{
    string name = obj.Name.ToString();
    if (filter != null && !name.Contains(filter, StringComparison.OrdinalIgnoreCase)) continue;
    string file = Path.Combine(outDir, name + ".uc");
    try
    {
        File.WriteAllText(file, obj.Decompile(), Encoding.UTF8);
        ok++;
    }
    catch (Exception ex)
    {
        File.WriteAllText(file, $"// Dekompilierung fehlgeschlagen: {ex}", Encoding.UTF8);
        fail++;
    }
}
Console.WriteLine($"{ok} Klassen dekompiliert, {fail} Fehler -> {outDir}");
return 0;

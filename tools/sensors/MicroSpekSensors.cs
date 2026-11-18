// MicroSpekSensors — tiny helper that exposes LibreHardwareMonitorLib sensors as JSON.
//
// Built with the .NET Framework 4.8 compiler that ships with Windows 10/11,
// so no .NET SDK or runtime install is required on the target machine.
//
//   MicroSpekSensors.exe            -> JSON on stdout
//   MicroSpekSensors.exe --quiet    -> same, without opening the driver log
//
// Exit codes: 0 = data collected, 1 = fatal error (JSON with "ok": false).

using System;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Text;
using LibreHardwareMonitor.Hardware;

internal static class Program
{
    private static string _outputPath;

    private static int Main(string[] args)
    {
        Console.OutputEncoding = new UTF8Encoding(false);
        AppDomain.CurrentDomain.AssemblyResolve += ResolveLocal;
        for (int i = 0; i < args.Length - 1; i++)
        {
            if (string.Equals(args[i], "--out", StringComparison.OrdinalIgnoreCase))
            {
                _outputPath = args[i + 1];
            }
        }
        try
        {
            var computer = new Computer
            {
                IsCpuEnabled = true,
                IsGpuEnabled = true,
                IsMotherboardEnabled = true,
                IsStorageEnabled = true,
                IsMemoryEnabled = true,
                IsControllerEnabled = false,
                IsNetworkEnabled = false,
                IsPsuEnabled = false,
                IsBatteryEnabled = false,
            };

            computer.Open();
            var json = new StringBuilder(8192);
            json.Append("{\"ok\":true,\"hardware\":[");
            bool first = true;
            foreach (IHardware hardware in computer.Hardware)
            {
                if (!first) json.Append(',');
                first = false;
                AppendHardware(json, hardware);
            }
            json.Append("]}");
            computer.Close();
            Write(json.ToString());
            return 0;
        }
        catch (Exception ex)
        {
            Write("{\"ok\":false,\"error\":" + Quote(ex.GetType().Name + ": " + ex.Message)
                + ",\"details\":" + Quote(ex.ToString()) + "}");
            return 1;
        }
    }

    private static Assembly ResolveLocal(object sender, ResolveEventArgs eventArgs)
    {
        try
        {
            string name = new AssemblyName(eventArgs.Name).Name;
            string folder = Path.GetDirectoryName(Assembly.GetExecutingAssembly().Location);
            string candidate = Path.Combine(folder, name + ".dll");
            return File.Exists(candidate) ? Assembly.LoadFrom(candidate) : null;
        }
        catch
        {
            return null;
        }
    }

    private static void AppendHardware(StringBuilder json, IHardware hardware)
    {
        try
        {
            hardware.Update();
        }
        catch
        {
            // A single unreadable device must not abort the whole report.
        }

        json.Append("{\"name\":").Append(Quote(hardware.Name))
            .Append(",\"type\":").Append(Quote(hardware.HardwareType.ToString()))
            .Append(",\"identifier\":").Append(Quote(hardware.Identifier.ToString()))
            .Append(",\"sensors\":[");

        bool firstSensor = true;
        foreach (ISensor sensor in hardware.Sensors)
        {
            if (!sensor.Value.HasValue) continue;
            if (!firstSensor) json.Append(',');
            firstSensor = false;
            json.Append("{\"type\":").Append(Quote(sensor.SensorType.ToString()))
                .Append(",\"name\":").Append(Quote(sensor.Name))
                .Append(",\"value\":").Append(Number(sensor.Value.Value));
            if (sensor.Min.HasValue) json.Append(",\"min\":").Append(Number(sensor.Min.Value));
            if (sensor.Max.HasValue) json.Append(",\"max\":").Append(Number(sensor.Max.Value));
            json.Append('}');
        }
        json.Append(']');

        json.Append(",\"children\":[");
        bool firstChild = true;
        foreach (IHardware child in hardware.SubHardware)
        {
            if (!firstChild) json.Append(',');
            firstChild = false;
            AppendHardware(json, child);
        }
        json.Append("]}");
    }

    private static string Number(float value)
    {
        if (float.IsNaN(value) || float.IsInfinity(value)) return "null";
        return value.ToString("0.###", CultureInfo.InvariantCulture);
    }

    private static string Quote(string text)
    {
        if (text == null) return "null";
        var sb = new StringBuilder(text.Length + 8);
        sb.Append('"');
        foreach (char ch in text)
        {
            switch (ch)
            {
                case '"': sb.Append("\\\""); break;
                case '\\': sb.Append("\\\\"); break;
                case '\n': sb.Append("\\n"); break;
                case '\r': sb.Append("\\r"); break;
                case '\t': sb.Append("\\t"); break;
                default:
                    if (ch < 0x20) sb.Append("\\u").Append(((int)ch).ToString("x4"));
                    else sb.Append(ch);
                    break;
            }
        }
        sb.Append('"');
        return sb.ToString();
    }

    private static void Write(string text)
    {
        if (!string.IsNullOrEmpty(_outputPath))
        {
            try
            {
                File.WriteAllText(_outputPath, text, new UTF8Encoding(false));
                return;
            }
            catch
            {
                // Fall back to stdout below.
            }
        }
        using (var stdout = new StreamWriter(Console.OpenStandardOutput(), new UTF8Encoding(false)))
        {
            stdout.Write(text);
            stdout.Flush();
        }
    }
}

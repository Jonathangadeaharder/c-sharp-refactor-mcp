using Microsoft.Extensions.Logging;
using System.Diagnostics;
using System.Text;
using System.Text.Json;
using System.Text.Json.Nodes;

namespace RoslynRefactorServer.Services;

/// <summary>
/// Generic LSP (Language Server Protocol) client for communicating with language servers
/// </summary>
public class LspClient : IAsyncDisposable
{
    private readonly Process _process;
    private readonly StreamWriter _stdin;
    private readonly StreamReader _stdout;
    private readonly ILogger _logger;
    private readonly SemaphoreSlim _requestLock = new(1, 1);
    private int _requestId = 0;

    public bool IsInitialized { get; private set; }
    public string LanguageId { get; }

    public LspClient(string languageId, string serverCommand, string[] serverArgs, ILogger logger)
    {
        LanguageId = languageId;
        _logger = logger;

        _process = new Process
        {
            StartInfo = new ProcessStartInfo
            {
                FileName = serverCommand,
                Arguments = string.Join(" ", serverArgs),
                UseShellExecute = false,
                RedirectStandardInput = true,
                RedirectStandardOutput = true,
                RedirectStandardError = true,
                CreateNoWindow = true
            }
        };

        _process.ErrorDataReceived += (sender, e) =>
        {
            if (!string.IsNullOrEmpty(e.Data))
            {
                _logger.LogDebug("[LSP {Language} stderr] {Message}", languageId, e.Data);
            }
        };

        _process.Start();
        _process.BeginErrorReadLine();

        _stdin = _process.StandardInput;
        _stdout = _process.StandardOutput;

        _logger.LogInformation("Started LSP server for {Language}: {Command}", languageId, serverCommand);
    }

    /// <summary>
    /// Initializes the LSP server
    /// </summary>
    public async Task InitializeAsync(string rootUri, CancellationToken cancellationToken = default)
    {
        var initParams = new
        {
            processId = Process.GetCurrentProcess().Id,
            rootUri = rootUri,
            capabilities = new
            {
                textDocument = new
                {
                    rename = new { prepareSupport = true },
                    references = new { },
                    definition = new { },
                    hover = new { }
                }
            }
        };

        var response = await SendRequestAsync<JsonNode>("initialize", initParams, cancellationToken);

        // Send initialized notification
        await SendNotificationAsync("initialized", new { }, cancellationToken);

        IsInitialized = true;
        _logger.LogInformation("LSP server for {Language} initialized", LanguageId);
    }

    /// <summary>
    /// Sends an LSP request and waits for response
    /// </summary>
    public async Task<TResponse?> SendRequestAsync<TResponse>(
        string method,
        object? parameters,
        CancellationToken cancellationToken = default)
    {
        await _requestLock.WaitAsync(cancellationToken);
        try
        {
            var id = ++_requestId;
            var request = new
            {
                jsonrpc = "2.0",
                id = id,
                method = method,
                @params = parameters
            };

            var json = JsonSerializer.Serialize(request);
            var message = $"Content-Length: {Encoding.UTF8.GetByteCount(json)}\r\n\r\n{json}";

            await _stdin.WriteAsync(message);
            await _stdin.FlushAsync();

            _logger.LogDebug("[LSP {Language}] Sent request: {Method}", LanguageId, method);

            // Read response
            var responseMessage = await ReadMessageAsync(cancellationToken);
            if (responseMessage == null)
            {
                throw new InvalidOperationException("No response from LSP server");
            }

            var responseJson = JsonSerializer.Deserialize<JsonNode>(responseMessage);
            if (responseJson?["error"] != null)
            {
                var error = responseJson["error"]?["message"]?.ToString() ?? "Unknown error";
                throw new InvalidOperationException($"LSP error: {error}");
            }

            var result = responseJson?["result"];
            if (result == null)
            {
                return default;
            }

            return JsonSerializer.Deserialize<TResponse>(result.ToJsonString());
        }
        finally
        {
            _requestLock.Release();
        }
    }

    /// <summary>
    /// Sends an LSP notification (no response expected)
    /// </summary>
    public async Task SendNotificationAsync(string method, object? parameters, CancellationToken cancellationToken = default)
    {
        var notification = new
        {
            jsonrpc = "2.0",
            method = method,
            @params = parameters
        };

        var json = JsonSerializer.Serialize(notification);
        var message = $"Content-Length: {Encoding.UTF8.GetByteCount(json)}\r\n\r\n{json}";

        await _stdin.WriteAsync(message);
        await _stdin.FlushAsync();

        _logger.LogDebug("[LSP {Language}] Sent notification: {Method}", LanguageId, method);
    }

    /// <summary>
    /// Opens a document in the LSP server
    /// </summary>
    public async Task DidOpenAsync(string uri, string languageId, string text, CancellationToken cancellationToken = default)
    {
        await SendNotificationAsync("textDocument/didOpen", new
        {
            textDocument = new
            {
                uri = uri,
                languageId = languageId,
                version = 1,
                text = text
            }
        }, cancellationToken);
    }

    /// <summary>
    /// Closes a document in the LSP server
    /// </summary>
    public async Task DidCloseAsync(string uri, CancellationToken cancellationToken = default)
    {
        await SendNotificationAsync("textDocument/didClose", new
        {
            textDocument = new { uri = uri }
        }, cancellationToken);
    }

    private async Task<string?> ReadMessageAsync(CancellationToken cancellationToken)
    {
        // Read headers
        var headers = new Dictionary<string, string>();
        while (true)
        {
            var line = await _stdout.ReadLineAsync();
            if (string.IsNullOrWhiteSpace(line))
            {
                break;
            }

            var parts = line.Split(':', 2);
            if (parts.Length == 2)
            {
                headers[parts[0].Trim()] = parts[1].Trim();
            }
        }

        if (!headers.TryGetValue("Content-Length", out var lengthStr) ||
            !int.TryParse(lengthStr, out var contentLength))
        {
            return null;
        }

        // Read content
        var buffer = new char[contentLength];
        var totalRead = 0;

        while (totalRead < contentLength)
        {
            var read = await _stdout.ReadAsync(buffer, totalRead, contentLength - totalRead);
            if (read == 0)
            {
                throw new InvalidOperationException("Unexpected end of stream");
            }
            totalRead += read;
        }

        return new string(buffer);
    }

    public async ValueTask DisposeAsync()
    {
        if (IsInitialized)
        {
            try
            {
                await SendRequestAsync<object>("shutdown", null, CancellationToken.None);
                await SendNotificationAsync("exit", null, CancellationToken.None);
            }
            catch (Exception ex)
            {
                _logger.LogWarning(ex, "Error shutting down LSP server for {Language}", LanguageId);
            }
        }

        _stdin?.Dispose();
        _stdout?.Dispose();

        if (!_process.HasExited)
        {
            _process.Kill(true);
        }

        _process?.Dispose();
        _requestLock?.Dispose();

        _logger.LogInformation("LSP server for {Language} disposed", LanguageId);
    }
}

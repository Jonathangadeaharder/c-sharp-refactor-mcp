namespace RoslynRefactorServer.Abstractions;

/// <summary>
/// Generic result wrapper for language provider operations
/// </summary>
public class ProviderResult<T>
{
    public bool Success { get; init; }
    public T? Data { get; init; }
    public string? Error { get; init; }
    public string? ErrorType { get; init; }

    public static ProviderResult<T> SuccessResult(T data)
    {
        return new ProviderResult<T>
        {
            Success = true,
            Data = data
        };
    }

    public static ProviderResult<T> ErrorResult(string error, string? errorType = null)
    {
        return new ProviderResult<T>
        {
            Success = false,
            Error = error,
            ErrorType = errorType
        };
    }

    public static ProviderResult<T> FromException(Exception ex)
    {
        return ErrorResult(ex.Message, ex.GetType().Name);
    }
}

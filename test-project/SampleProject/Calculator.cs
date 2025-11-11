namespace SampleProject;

/// <summary>
/// A simple calculator class for demonstration
/// </summary>
public class Calculator
{
    private int _lastResult;

    public int AddNumbers(int a, int b)
    {
        var sum = a + b;
        _lastResult = sum;
        LogOperation("Add", a, b, sum);
        return sum;
    }

    public int MultiplyNumbers(int x, int y)
    {
        var product = x * y;
        _lastResult = product;
        LogOperation("Multiply", x, y, product);
        return product;
    }

    private void LogOperation(string operation, int operand1, int operand2, int result)
    {
        Console.WriteLine($"{operation}: {operand1} and {operand2} = {result}");
    }

    public int GetLastResult()
    {
        return _lastResult;
    }
}

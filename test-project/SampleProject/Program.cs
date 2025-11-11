namespace SampleProject;

public class Program
{
    public static void Main(string[] args)
    {
        var calculator = new Calculator();
        var result = calculator.AddNumbers(5, 10);
        Console.WriteLine($"Result: {result}");

        var processor = new DataProcessor();
        processor.ProcessData("Hello, World!");
    }
}

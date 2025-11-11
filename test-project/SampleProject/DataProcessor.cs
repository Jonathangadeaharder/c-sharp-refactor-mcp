namespace SampleProject;

public class DataProcessor
{
    public void ProcessData(string data)
    {
        if (string.IsNullOrEmpty(data))
        {
            Console.WriteLine("No data to process");
            return;
        }

        var upperData = data.ToUpper();
        var length = data.Length;
        var reversed = ReverseString(data);

        Console.WriteLine($"Original: {data}");
        Console.WriteLine($"Upper: {upperData}");
        Console.WriteLine($"Length: {length}");
        Console.WriteLine($"Reversed: {reversed}");
    }

    private string ReverseString(string input)
    {
        char[] charArray = input.ToCharArray();
        Array.Reverse(charArray);
        return new string(charArray);
    }
}

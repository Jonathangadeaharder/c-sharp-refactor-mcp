using FluentAssertions;
using RoslynRefactorServer.Models;
using Xunit;

namespace RoslynRefactorServer.Tests.Models;

public class ModelTests
{
    [Fact]
    public void ReferenceLocation_ShouldInitializeWithDefaultValues()
    {
        // Arrange & Act
        var location = new ReferenceLocation();

        // Assert
        location.FilePath.Should().BeEmpty();
        location.StartLine.Should().Be(0);
        location.StartColumn.Should().Be(0);
        location.EndLine.Should().Be(0);
        location.EndColumn.Should().Be(0);
        location.CodeSnippet.Should().BeEmpty();
    }

    [Fact]
    public void ReferenceLocation_ShouldSetAndGetProperties()
    {
        // Arrange & Act
        var location = new ReferenceLocation
        {
            FilePath = "/path/to/file.cs",
            StartLine = 10,
            StartColumn = 5,
            EndLine = 10,
            EndColumn = 15,
            CodeSnippet = "var x = 42;"
        };

        // Assert
        location.FilePath.Should().Be("/path/to/file.cs");
        location.StartLine.Should().Be(10);
        location.StartColumn.Should().Be(5);
        location.EndLine.Should().Be(10);
        location.EndColumn.Should().Be(15);
        location.CodeSnippet.Should().Be("var x = 42;");
    }

    [Fact]
    public void DiagnosticInfo_ShouldInitializeWithDefaultValues()
    {
        // Arrange & Act
        var diagnostic = new DiagnosticInfo();

        // Assert
        diagnostic.Id.Should().BeEmpty();
        diagnostic.Message.Should().BeEmpty();
        diagnostic.Severity.Should().BeEmpty();
        diagnostic.FilePath.Should().BeEmpty();
        diagnostic.Line.Should().Be(0);
        diagnostic.Column.Should().Be(0);
    }

    [Fact]
    public void DiagnosticInfo_ShouldSetAndGetProperties()
    {
        // Arrange & Act
        var diagnostic = new DiagnosticInfo
        {
            Id = "CS0103",
            Message = "The name 'foo' does not exist in the current context",
            Severity = "Error",
            FilePath = "/path/to/file.cs",
            Line = 42,
            Column = 10
        };

        // Assert
        diagnostic.Id.Should().Be("CS0103");
        diagnostic.Message.Should().Contain("does not exist");
        diagnostic.Severity.Should().Be("Error");
        diagnostic.FilePath.Should().Be("/path/to/file.cs");
        diagnostic.Line.Should().Be(42);
        diagnostic.Column.Should().Be(10);
    }
}

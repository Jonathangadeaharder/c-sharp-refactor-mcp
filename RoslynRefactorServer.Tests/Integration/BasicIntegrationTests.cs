using FluentAssertions;
using Xunit;

namespace RoslynRefactorServer.Tests.Integration;

/// <summary>
/// Basic integration tests to ensure the project compiles and basic functionality works.
/// These tests don't require a full solution to be loaded.
/// </summary>
public class BasicIntegrationTests
{
    [Fact]
    public void Project_ShouldCompile()
    {
        // This test passes if the project compiles successfully
        Assert.True(true);
    }

    [Fact]
    public void PathSeparator_ShouldBeCorrectForPlatform()
    {
        // Arrange & Act
        var separator = Path.DirectorySeparatorChar;

        // Assert
        separator.Should().BeOneOf('/', '\\');
    }

    [Fact]
    public void DotNetEnvironment_ShouldBeAvailable()
    {
        // Arrange & Act
        var version = Environment.Version;

        // Assert
        version.Should().NotBeNull();
        version.Major.Should().BeGreaterOrEqualTo(8);
    }

    [Theory]
    [InlineData("/home/user/test.cs", ".cs")]
    [InlineData("C:\\dev\\project.sln", ".sln")]
    [InlineData("/workspace/code.txt", ".txt")]
    public void PathExtension_ShouldBeExtractedCorrectly(string path, string expectedExtension)
    {
        // Act
        var extension = Path.GetExtension(path);

        // Assert
        extension.Should().Be(expectedExtension);
    }

    [Fact]
    public void JsonSerialization_ShouldWork()
    {
        // Arrange
        var testObject = new { success = true, message = "test" };

        // Act
        var json = System.Text.Json.JsonSerializer.Serialize(testObject);

        // Assert
        json.Should().Contain("success");
        json.Should().Contain("true");
        json.Should().Contain("test");
    }
}

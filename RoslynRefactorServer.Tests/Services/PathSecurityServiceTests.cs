using FluentAssertions;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.Logging;
using Moq;
using RoslynRefactorServer.Services;
using System.Security;
using Xunit;

namespace RoslynRefactorServer.Tests.Services;

public class PathSecurityServiceTests
{
    private readonly Mock<ILogger<PathSecurityService>> _loggerMock;
    private readonly IConfiguration _configuration;

    public PathSecurityServiceTests()
    {
        _loggerMock = new Mock<ILogger<PathSecurityService>>();

        // Setup test configuration with allowed paths
        var inMemorySettings = new Dictionary<string, string>
        {
            {"Security:AllowedRootPaths:0", "/home/user/projects"},
            {"Security:AllowedRootPaths:1", "/workspace"},
            {"Security:AllowedRootPaths:2", "C:\\dev"}
        };

        _configuration = new ConfigurationBuilder()
            .AddInMemoryCollection(inMemorySettings!)
            .Build();
    }

    [Fact]
    public void ValidateAndNormalizePath_WithAllowedPath_ShouldSucceed()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var testPath = "/home/user/projects/myproject/file.cs";

        // Act
        var result = service.ValidateAndNormalizePath(testPath);

        // Assert
        result.Should().NotBeNull();
        result.Should().Contain("projects");
    }

    [Fact]
    public void ValidateAndNormalizePath_WithDisallowedPath_ShouldThrowSecurityException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var testPath = "/etc/passwd";

        // Act & Assert
        var exception = Assert.Throws<SecurityException>(() =>
            service.ValidateAndNormalizePath(testPath));

        exception.Message.Should().Contain("Access denied");
        exception.Message.Should().Contain("/etc/passwd");
    }

    [Fact]
    public void ValidateAndNormalizePath_WithPathTraversal_ShouldThrowSecurityException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var testPath = "/home/user/projects/../../../etc/passwd";

        // Act & Assert
        var exception = Assert.Throws<SecurityException>(() =>
            service.ValidateAndNormalizePath(testPath));

        exception.Message.Should().Contain("Access denied");
    }

    [Fact]
    public void ValidateAndNormalizePath_WithNullPath_ShouldThrowArgumentException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);

        // Act & Assert
        Assert.Throws<ArgumentException>(() =>
            service.ValidateAndNormalizePath(null!));
    }

    [Fact]
    public void ValidateAndNormalizePath_WithEmptyPath_ShouldThrowArgumentException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);

        // Act & Assert
        Assert.Throws<ArgumentException>(() =>
            service.ValidateAndNormalizePath(""));
    }

    [Fact]
    public void ValidateSolutionFile_WithValidSolutionFile_ShouldSucceed()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var tempDir = Path.Combine("/home/user/projects", "temp_test");
        Directory.CreateDirectory(tempDir);
        var solutionFile = Path.Combine(tempDir, "test.sln");
        File.WriteAllText(solutionFile, "# Test solution");

        try
        {
            // Act
            service.ValidateSolutionFile(solutionFile);

            // Assert - no exception thrown
            Assert.True(true);
        }
        finally
        {
            // Cleanup
            if (File.Exists(solutionFile))
                File.Delete(solutionFile);
            if (Directory.Exists(tempDir))
                Directory.Delete(tempDir);
        }
    }

    [Fact]
    public void ValidateSolutionFile_WithNonSolutionExtension_ShouldThrowArgumentException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var tempDir = Path.Combine("/home/user/projects", "temp_test");
        Directory.CreateDirectory(tempDir);
        var wrongFile = Path.Combine(tempDir, "test.txt");
        File.WriteAllText(wrongFile, "# Not a solution");

        try
        {
            // Act & Assert
            var exception = Assert.Throws<ArgumentException>(() =>
                service.ValidateSolutionFile(wrongFile));

            exception.Message.Should().Contain("not a solution file");
        }
        finally
        {
            // Cleanup
            if (File.Exists(wrongFile))
                File.Delete(wrongFile);
            if (Directory.Exists(tempDir))
                Directory.Delete(tempDir);
        }
    }

    [Fact]
    public void ValidateSolutionFile_WithNonExistentFile_ShouldThrowFileNotFoundException()
    {
        // Arrange
        var service = new PathSecurityService(_configuration, _loggerMock.Object);
        var nonExistentFile = "/home/user/projects/nonexistent.sln";

        // Act & Assert
        Assert.Throws<FileNotFoundException>(() =>
            service.ValidateSolutionFile(nonExistentFile));
    }

    [Fact]
    public void Constructor_WithNoAllowedPaths_ShouldLogWarning()
    {
        // Arrange
        var emptyConfig = new ConfigurationBuilder().Build();

        // Act
        var service = new PathSecurityService(emptyConfig, _loggerMock.Object);

        // Assert
        _loggerMock.Verify(
            x => x.Log(
                LogLevel.Warning,
                It.IsAny<EventId>(),
                It.Is<It.IsAnyType>((v, t) => v.ToString()!.Contains("No allowed root paths")),
                It.IsAny<Exception>(),
                It.IsAny<Func<It.IsAnyType, Exception?, string>>()),
            Times.Once);
    }
}

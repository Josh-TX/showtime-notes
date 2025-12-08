using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

public record SignupRequest(string InviteCode, string Username, string Password);

[ApiController]
[Route("api")]
public class ApiController(SignInManager<IdentityUser> _signInManager, UserManager<IdentityUser> _userManager) : ControllerBase
{

    [HttpPost("login")]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var user = await _userManager.FindByNameAsync(request.Username);
        if (user == null)
        {
            return Unauthorized(new { message = "Invalid username or password" });
        }

        var result = await _signInManager.PasswordSignInAsync(
            user,
            request.Password,
            isPersistent: true, // Remember me
            lockoutOnFailure: false
        );

        if (result.Succeeded)
        {
            return Ok(new { message = "Login successful" });
        }

        return Unauthorized(new { message = "Invalid username or password" });
    }


    [HttpPost("signup")]
    public async Task<IActionResult> Signup([FromBody] SignupRequest request)
    {
        // Validate invite code (change this to your actual invite code)
        const string validInviteCode = "cbc2025";
        if (request.InviteCode != validInviteCode)
        {
            return BadRequest(new { message = "Invalid invite code" });
        }

        // Check if user already exists
        var existingUser = await _userManager.FindByNameAsync(request.Username);
        if (existingUser != null)
        {
            return BadRequest(new { message = "Username already taken" });
        }

        // Create new user
        var user = new IdentityUser { UserName = request.Username };
        var result = await _userManager.CreateAsync(user, request.Password);

        if (!result.Succeeded)
        {
            var errors = string.Join(", ", result.Errors.Select(e => e.Description));
            return BadRequest(new { message = errors });
        }

        // Sign them in automatically after signup
        await _signInManager.SignInAsync(user, isPersistent: true);

        return Ok(new { message = "Signup successful" });
    }
}

public record LoginRequest(string Username, string Password);
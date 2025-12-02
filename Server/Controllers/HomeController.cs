using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;

public class HomeController(SignInManager<IdentityUser> _signInManager) : Controller
{

    private static byte[]? _cachedIndexHtml;

    [HttpGet("/")]
    public IActionResult Index()
    {
        if (User.Identity?.IsAuthenticated ?? false)
        {
            if (_cachedIndexHtml == null || true)
            {
                _cachedIndexHtml = System.IO.File.ReadAllBytes(Path.Combine(Directory.GetCurrentDirectory(), "wwwroot", "index.html"));
            }
            return File(_cachedIndexHtml, "text/html");
        }
        return RedirectToAction(nameof(Login));
    }

    [HttpGet("/login")]
    public IActionResult Login()
    {
        if (User.Identity?.IsAuthenticated ?? false)
        {
            return RedirectToAction(nameof(Index));
        }
        return View("Auth", false); // IsSignup=false
    }

    [HttpGet("/signup")]
    public IActionResult Signup()
    {
        if (User.Identity?.IsAuthenticated ?? false)
        {
            return RedirectToAction(nameof(Index));
        }
        return View("Auth", true); // IsSignup=true
    }

    [HttpGet("logout")]
    public async Task<IActionResult> Logout()
    {
        if (User.Identity?.IsAuthenticated ?? false)
        {
            await _signInManager.SignOutAsync();
            return Ok("Logged out successfully");
        } else
        {
            return Ok("you were already logged out");
        }
    }
}
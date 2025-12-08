using Microsoft.AspNetCore.SignalR;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Identity.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore;

var builder = WebApplication.CreateBuilder(args);
var services = builder.Services;

services.AddDbContext<IdentityDbContext>(options => options.UseSqlite("Data Source=identity.db"));
services.AddIdentity<IdentityUser, IdentityRole>(options =>
{
    options.User.AllowedUserNameCharacters = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_";
    options.Password.RequireLowercase = false;
    options.Password.RequireUppercase = false;
    options.Password.RequireDigit = false;
    options.Password.RequireNonAlphanumeric = false;
    options.Password.RequiredLength = 4;
}).AddSignInManager().AddEntityFrameworkStores<IdentityDbContext>();

builder.Services.AddControllersWithViews();
builder.Services.AddSingleton<ActiveUserService>();
builder.Services.AddSingleton<SceneService>();
builder.Services.AddSignalR(options =>
{
    var maxkb = 200;
    options.MaximumReceiveMessageSize = 1024 * maxkb;
    options.EnableDetailedErrors = true;
});
services.AddHttpContextAccessor();

var app = builder.Build();
app.UseAuthentication();
app.UseAuthorization();
app.UseStaticFiles();
app.MapControllers();
app.MapHub<SignalRHub>("main-hub");
using (var scope = app.Services.CreateScope())
{
    var db = scope.ServiceProvider.GetRequiredService<IdentityDbContext>();
    db.Database.EnsureCreated();
}
app.Run();
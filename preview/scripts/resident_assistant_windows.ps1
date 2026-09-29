param(
    [string]$InstallRoot = "$env:LOCALAPPDATA\LocalAssistantHost"
)

$ErrorActionPreference = "Stop"

Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing
Add-Type -AssemblyName System.Net.Http
Add-Type -AssemblyName PresentationFramework
Add-Type -AssemblyName PresentationCore
Add-Type -AssemblyName WindowsBase
Add-Type -AssemblyName System.Xaml
Add-Type -AssemblyName WindowsFormsIntegration

$hotkeyTypeSource = @"
using System;
using System.Runtime.InteropServices;
using System.Windows.Forms;

public sealed class ResidentAssistantHotkeyForm : Form
{
    private const int HotkeyId = 0x4A41;
    private const int WmHotkey = 0x0312;
    private const uint ModAlt = 0x0001;
    private const uint ModControl = 0x0002;
    private const uint ModNoRepeat = 0x4000;
    private const uint VkSpace = 0x20;
    private bool registered;

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool RegisterHotKey(IntPtr hWnd, int id, uint modifiers, uint virtualKey);

    [DllImport("user32.dll", SetLastError = true)]
    private static extern bool UnregisterHotKey(IntPtr hWnd, int id);

    public event EventHandler HotkeyPressed;

    public bool RegistrationSucceeded { get { return registered; } }

    public ResidentAssistantHotkeyForm()
    {
        ShowInTaskbar = false;
        FormBorderStyle = FormBorderStyle.FixedToolWindow;
        StartPosition = FormStartPosition.Manual;
        Location = new System.Drawing.Point(-32000, -32000);
        Size = new System.Drawing.Size(1, 1);
        Opacity = 0;
    }

    protected override void OnHandleCreated(EventArgs e)
    {
        base.OnHandleCreated(e);
        registered = RegisterHotKey(Handle, HotkeyId, ModControl | ModAlt | ModNoRepeat, VkSpace);
    }

    protected override void OnHandleDestroyed(EventArgs e)
    {
        if (registered)
        {
            UnregisterHotKey(Handle, HotkeyId);
            registered = false;
        }
        base.OnHandleDestroyed(e);
    }

    protected override void SetVisibleCore(bool value)
    {
        base.SetVisibleCore(false);
    }

    protected override void WndProc(ref Message message)
    {
        if (message.Msg == WmHotkey && message.WParam.ToInt32() == HotkeyId)
        {
            EventHandler handler = HotkeyPressed;
            if (handler != null)
            {
                handler(this, EventArgs.Empty);
            }
        }
        base.WndProc(ref message);
    }
}
"@
Add-Type -TypeDefinition $hotkeyTypeSource -ReferencedAssemblies @(
    "System.Windows.Forms.dll",
    "System.Drawing.dll"
)

$configPath = Join-Path $InstallRoot "host_config.json"
$tokenPath = Join-Path $InstallRoot "api_key.dpapi"
$heartbeatPath = Join-Path $InstallRoot "heartbeat.json"
$stopRequestPath = Join-Path $InstallRoot "stop.request"
$logPath = Join-Path $InstallRoot "host-events.jsonl"
$utf8NoBom = New-Object System.Text.UTF8Encoding($false)

if (-not (Test-Path -LiteralPath $configPath -PathType Leaf)) {
    throw "Resident host configuration was not found. Run install_resident_host_windows.ps1 first."
}
if (-not (Test-Path -LiteralPath $tokenPath -PathType Leaf)) {
    throw "Resident host API credential was not found. Run the installer again."
}

$settings = Get-Content -LiteralPath $configPath -Raw | ConvertFrom-Json
$assistantName = [string]$settings.assistant_name
$endpoint = [string]$settings.endpoint
$conversation = [string]$settings.conversation

if ([string]::IsNullOrWhiteSpace($assistantName)) {
    $assistantName = "Hermes"
}
if ([string]::IsNullOrWhiteSpace($conversation)) {
    $conversation = "resident-main"
}

$endpointUri = [Uri]$endpoint
$loopbackNames = @("127.0.0.1", "localhost", "::1")
if ($endpointUri.Scheme -ne "http" -or $loopbackNames -notcontains $endpointUri.Host) {
    throw "Resident host refuses a non-loopback or non-HTTP Hermes endpoint."
}

function Write-HostEvent {
    param(
        [Parameter(Mandatory = $true)][string]$Event,
        [string]$Outcome = "ok",
        [int]$DurationMs = 0
    )

    try {
        if ((Test-Path -LiteralPath $logPath -PathType Leaf) -and
            (Get-Item -LiteralPath $logPath).Length -gt 1048576) {
            $archivePath = Join-Path $InstallRoot "host-events.previous.jsonl"
            Move-Item -LiteralPath $logPath -Destination $archivePath -Force
        }
        $entry = [ordered]@{
            timestamp = [DateTimeOffset]::UtcNow.ToString("o")
            event = $Event
            outcome = $Outcome
            duration_ms = $DurationMs
        } | ConvertTo-Json -Compress
        [IO.File]::AppendAllText($logPath, $entry + [Environment]::NewLine, $utf8NoBom)
    } catch {
        # Logging must never block or expose a user's command or response.
    }
}

function Get-PlaintextSecret {
    param([Parameter(Mandatory = $true)][string]$Path)

    $secure = (Get-Content -LiteralPath $Path -Raw).Trim() | ConvertTo-SecureString
    $pointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($secure)
    try {
        return [Runtime.InteropServices.Marshal]::PtrToStringBSTR($pointer)
    } finally {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($pointer)
    }
}

function Resolve-CommandPath {
    param(
        [Parameter(Mandatory = $true)][string]$Name,
        [Parameter(Mandatory = $true)][string[]]$KnownPaths
    )

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return $command.Source
    }
    foreach ($candidate in $KnownPaths) {
        if (Test-Path -LiteralPath $candidate -PathType Leaf) {
            return $candidate
        }
    }
    return $null
}

function Test-HttpEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [int]$TimeoutSeconds = 2
    )
    try {
        $null = Invoke-RestMethod -Uri $Uri -Method Get -TimeoutSec $TimeoutSeconds
        return $true
    } catch {
        return $false
    }
}

function Start-HiddenProcess {
    param(
        [Parameter(Mandatory = $true)][string]$FilePath,
        [Parameter(Mandatory = $true)][string]$Arguments
    )

    $startInfo = New-Object System.Diagnostics.ProcessStartInfo
    $startInfo.FileName = $FilePath
    $startInfo.Arguments = $Arguments
    $startInfo.UseShellExecute = $false
    $startInfo.CreateNoWindow = $true
    $startInfo.WindowStyle = [Diagnostics.ProcessWindowStyle]::Hidden
    return [Diagnostics.Process]::Start($startInfo)
}

function Wait-ForEndpoint {
    param(
        [Parameter(Mandatory = $true)][string]$Uri,
        [int]$Seconds = 30
    )
    $deadline = [DateTime]::UtcNow.AddSeconds($Seconds)
    do {
        if (Test-HttpEndpoint -Uri $Uri) {
            return $true
        }
        Start-Sleep -Milliseconds 500
    } while ([DateTime]::UtcNow -lt $deadline)
    return $false
}

function Ensure-LocalRuntime {
    $ollamaHealth = "http://127.0.0.1:11434/api/version"
    if (-not (Test-HttpEndpoint -Uri $ollamaHealth)) {
        $ollamaPath = Resolve-CommandPath -Name "ollama.exe" -KnownPaths @(
            (Join-Path $env:LOCALAPPDATA "Programs\Ollama\ollama.exe")
        )
        if (-not $ollamaPath) {
            throw "Ollama is not reachable and ollama.exe could not be found."
        }
        $null = Start-HiddenProcess -FilePath $ollamaPath -Arguments "serve"
        if (-not (Wait-ForEndpoint -Uri $ollamaHealth -Seconds 25)) {
            throw "Ollama did not become ready on its loopback endpoint."
        }
    }

    $hermesHealth = $endpoint.TrimEnd("/") + "/health"
    if (-not (Test-HttpEndpoint -Uri $hermesHealth)) {
        $hermesPath = Resolve-CommandPath -Name "hermes.exe" -KnownPaths @(
            (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\bin\hermes.exe"),
            (Join-Path $env:LOCALAPPDATA "hermes\hermes-agent\venv\Scripts\hermes.exe")
        )
        if (-not $hermesPath) {
            throw "Hermes is not reachable and hermes.exe could not be found."
        }
        $gatewayStarter = Start-HiddenProcess -FilePath $hermesPath -Arguments "gateway start"
        $null = $gatewayStarter.WaitForExit(15000)
        if (-not (Wait-ForEndpoint -Uri $hermesHealth -Seconds 30)) {
            throw "Hermes gateway did not become ready on its loopback endpoint."
        }
    }
}

function ConvertTo-CypherBrush {
    param([Parameter(Mandatory = $true)][string]$Color)
    $converter = New-Object System.Windows.Media.BrushConverter
    return $converter.ConvertFromString($Color)
}

function Add-CypherInlineText {
    param(
        [Parameter(Mandatory = $true)][System.Windows.Documents.Paragraph]$Paragraph,
        [AllowEmptyString()][string]$Text
    )

    $pattern = '(\*\*(?<bold>.+?)\*\*)|(`(?<code>[^`]+)`)'
    $cursor = 0
    foreach ($match in [regex]::Matches($Text, $pattern)) {
        if ($match.Index -gt $cursor) {
            $plainRun = New-Object System.Windows.Documents.Run
            $plainRun.Text = $Text.Substring($cursor, $match.Index - $cursor)
            $Paragraph.Inlines.Add($plainRun) | Out-Null
        }
        $formattedRun = New-Object System.Windows.Documents.Run
        if ($match.Groups['bold'].Success) {
            $formattedRun.Text = $match.Groups['bold'].Value
            $formattedRun.FontWeight = [Windows.FontWeights]::SemiBold
            $formattedRun.Foreground = ConvertTo-CypherBrush -Color '#EAF7FF'
        } else {
            $formattedRun.Text = $match.Groups['code'].Value
            $formattedRun.FontFamily = New-Object System.Windows.Media.FontFamily('Consolas')
            $formattedRun.Foreground = ConvertTo-CypherBrush -Color '#72E6D1'
            $formattedRun.Background = ConvertTo-CypherBrush -Color '#182731'
        }
        $Paragraph.Inlines.Add($formattedRun) | Out-Null
        $cursor = $match.Index + $match.Length
    }
    if ($cursor -lt $Text.Length) {
        $tailRun = New-Object System.Windows.Documents.Run
        $tailRun.Text = $Text.Substring($cursor)
        $Paragraph.Inlines.Add($tailRun) | Out-Null
    }
}

function Set-CypherResponseText {
    param([AllowEmptyString()][string]$Text)

    if (-not $script:assistantResponse) {
        return
    }
    $script:lastResponseText = $Text
    $document = New-Object System.Windows.Documents.FlowDocument
    $document.PagePadding = New-Object System.Windows.Thickness(0)
    $document.FontFamily = New-Object System.Windows.Media.FontFamily('Segoe UI')
    $document.FontSize = 15
    $document.Foreground = ConvertTo-CypherBrush -Color '#D8E4EC'

    if ([string]::IsNullOrWhiteSpace($Text)) {
        $Text = "Ready when you are.`n`nAsk a question, make a plan, or give me a task."
    }
    foreach ($line in ($Text -split "\r?\n")) {
        $paragraph = New-Object System.Windows.Documents.Paragraph
        $paragraph.Margin = New-Object System.Windows.Thickness(0, 0, 0, 7)
        $displayLine = $line
        if ($line -match '^\s*(#{1,3})\s+(.+)$') {
            $level = $Matches[1].Length
            $displayLine = $Matches[2]
            $paragraph.FontWeight = [Windows.FontWeights]::SemiBold
            $paragraph.Foreground = ConvertTo-CypherBrush -Color '#F1FAFF'
            $paragraph.FontSize = if ($level -eq 1) { 22 } elseif ($level -eq 2) { 18 } else { 16 }
            $paragraph.Margin = New-Object System.Windows.Thickness(0, 8, 0, 9)
        } elseif ($line -match '^\s*[-*]\s+(.+)$') {
            $displayLine = "- " + $Matches[1]
            $paragraph.Margin = New-Object System.Windows.Thickness(14, 0, 0, 5)
        }
        Add-CypherInlineText -Paragraph $paragraph -Text $displayLine
        $document.Blocks.Add($paragraph) | Out-Null
    }
    $script:assistantResponse.Document = $document
    $script:assistantResponse.ScrollToEnd()
}

function Set-CypherStatus {
    param(
        [Parameter(Mandatory = $true)][string]$Text,
        [string]$Color = '#4DE3C1',
        [bool]$Busy = $false
    )

    if (-not $script:assistantStatus) {
        return
    }
    $script:assistantStatus.Text = $Text.ToUpperInvariant()
    $script:assistantStatus.Foreground = ConvertTo-CypherBrush -Color $Color
    $script:assistantStatusDot.Fill = ConvertTo-CypherBrush -Color $Color
    $script:assistantProgress.Visibility = if ($Busy) {
        [Windows.Visibility]::Visible
    } else {
        [Windows.Visibility]::Collapsed
    }
    $script:assistantProgress.IsIndeterminate = $Busy
    $script:assistantInput.IsEnabled = -not $Busy
    $script:assistantSend.IsEnabled = -not $Busy
    $script:assistantNewChat.IsEnabled = -not $Busy
}

function Initialize-CypherWindow {
    if ($script:assistantWindow) {
        return
    }

    $xaml = @'
<Window xmlns="http://schemas.microsoft.com/winfx/2006/xaml/presentation"
        xmlns:x="http://schemas.microsoft.com/winfx/2006/xaml"
        Title="Cypher" Width="860" Height="640" MinWidth="680" MinHeight="500"
        WindowStartupLocation="CenterScreen" WindowStyle="None" AllowsTransparency="True"
        Background="Transparent" ResizeMode="CanResizeWithGrip" ShowInTaskbar="False"
        Topmost="True" UseLayoutRounding="True" SnapsToDevicePixels="True"
        FontFamily="Segoe UI">
    <Window.Resources>
        <Style x:Key="CypherButton" TargetType="{x:Type Button}">
            <Setter Property="Foreground" Value="#E6F2F8"/>
            <Setter Property="Background" Value="#172630"/>
            <Setter Property="BorderBrush" Value="#29414F"/>
            <Setter Property="BorderThickness" Value="1"/>
            <Setter Property="Padding" Value="16,9"/>
            <Setter Property="FontSize" Value="13"/>
            <Setter Property="Cursor" Value="Hand"/>
            <Setter Property="Template">
                <Setter.Value>
                    <ControlTemplate TargetType="{x:Type Button}">
                        <Border x:Name="Chrome" CornerRadius="8" Background="{TemplateBinding Background}"
                                BorderBrush="{TemplateBinding BorderBrush}" BorderThickness="{TemplateBinding BorderThickness}"
                                Padding="{TemplateBinding Padding}">
                            <ContentPresenter HorizontalAlignment="Center" VerticalAlignment="Center"/>
                        </Border>
                        <ControlTemplate.Triggers>
                            <Trigger Property="IsMouseOver" Value="True">
                                <Setter TargetName="Chrome" Property="Background" Value="#203B48"/>
                                <Setter TargetName="Chrome" Property="BorderBrush" Value="#4DE3C1"/>
                            </Trigger>
                            <Trigger Property="IsPressed" Value="True">
                                <Setter TargetName="Chrome" Property="Background" Value="#112029"/>
                            </Trigger>
                            <Trigger Property="IsEnabled" Value="False">
                                <Setter TargetName="Chrome" Property="Opacity" Value="0.45"/>
                            </Trigger>
                        </ControlTemplate.Triggers>
                    </ControlTemplate>
                </Setter.Value>
            </Setter>
        </Style>
    </Window.Resources>
    <Border CornerRadius="18" Background="#F211171E" BorderBrush="#314552" BorderThickness="1">
        <Border.Effect>
            <DropShadowEffect Color="#000000" BlurRadius="30" ShadowDepth="8" Opacity="0.55"/>
        </Border.Effect>
        <Grid Margin="24">
            <Grid.RowDefinitions>
                <RowDefinition Height="54"/>
                <RowDefinition Height="*"/>
                <RowDefinition Height="4"/>
                <RowDefinition Height="Auto"/>
                <RowDefinition Height="34"/>
            </Grid.RowDefinitions>

            <Grid x:Name="TitleBar" Grid.Row="0" Background="Transparent">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="46"/>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="44"/>
                </Grid.ColumnDefinitions>
                <Grid Width="34" Height="34" HorizontalAlignment="Left" VerticalAlignment="Center">
                    <Ellipse Stroke="#4DE3C1" StrokeThickness="2" Opacity="0.85">
                        <Ellipse.Effect>
                            <DropShadowEffect Color="#4DE3C1" BlurRadius="10" ShadowDepth="0" Opacity="0.65"/>
                        </Ellipse.Effect>
                        <Ellipse.Triggers>
                            <EventTrigger RoutedEvent="FrameworkElement.Loaded">
                                <BeginStoryboard>
                                    <Storyboard RepeatBehavior="Forever" AutoReverse="True">
                                        <DoubleAnimation Storyboard.TargetProperty="Opacity" From="0.45" To="1" Duration="0:0:1.8"/>
                                    </Storyboard>
                                </BeginStoryboard>
                            </EventTrigger>
                        </Ellipse.Triggers>
                    </Ellipse>
                    <Ellipse Width="8" Height="8" Fill="#4DE3C1"/>
                </Grid>
                <StackPanel Grid.Column="1" VerticalAlignment="Center">
                    <TextBlock x:Name="AssistantTitle" Text="CYPHER" Foreground="#F2FAFE" FontSize="18" FontWeight="SemiBold"/>
                    <TextBlock Text="LOCAL RESIDENT ASSISTANT" Foreground="#6F8795" FontSize="10" Margin="0,2,0,0"/>
                </StackPanel>
                <Border Grid.Column="2" CornerRadius="10" BorderBrush="#29414F" BorderThickness="1"
                        Background="#111D24" Padding="10,5" VerticalAlignment="Center" Margin="0,0,12,0">
                    <StackPanel Orientation="Horizontal">
                        <Ellipse x:Name="StatusDot" Width="7" Height="7" Fill="#4DE3C1" Margin="0,0,7,0"/>
                        <TextBlock x:Name="StatusText" Text="READY" Foreground="#4DE3C1" FontSize="11" FontWeight="SemiBold"/>
                    </StackPanel>
                </Border>
                <Button x:Name="CloseButton" Grid.Column="3" Content="X" Style="{StaticResource CypherButton}"
                        Padding="10,6" Background="Transparent" BorderBrush="Transparent" FontSize="12"/>
            </Grid>

            <Border Grid.Row="1" CornerRadius="12" Background="#B80D141A" BorderBrush="#253640"
                    BorderThickness="1" Margin="0,10,0,14" Padding="20">
                <RichTextBox x:Name="ResponseBox" Background="Transparent" Foreground="#D8E4EC"
                             BorderThickness="0" IsReadOnly="True" IsDocumentEnabled="True"
                             VerticalScrollBarVisibility="Auto" HorizontalScrollBarVisibility="Disabled"
                             FontFamily="Segoe UI" FontSize="15" SelectionBrush="#376C78">
                    <FlowDocument PagePadding="0"/>
                </RichTextBox>
            </Border>

            <ProgressBar x:Name="Progress" Grid.Row="2" Height="2" Visibility="Collapsed"
                         Foreground="#4DE3C1" Background="#17252E" BorderThickness="0"/>

            <Border Grid.Row="3" CornerRadius="12" Background="#111B22" BorderBrush="#314651"
                    BorderThickness="1" Margin="0,14,0,10" Padding="14,10">
                <Grid>
                    <Grid.ColumnDefinitions>
                        <ColumnDefinition Width="*"/>
                        <ColumnDefinition Width="Auto"/>
                    </Grid.ColumnDefinitions>
                    <TextBox x:Name="InputBox" Grid.Column="0" Background="Transparent" Foreground="#EFF8FC"
                             BorderThickness="0" FontSize="15" MinHeight="54" MaxHeight="130"
                             TextWrapping="Wrap" AcceptsReturn="True" VerticalScrollBarVisibility="Auto"
                             CaretBrush="#4DE3C1" MaxLength="8000" Padding="2,6,12,6"
                             ToolTip="Enter to send. Shift+Enter for a new line."/>
                    <Button x:Name="SendButton" Grid.Column="1" Content="SEND" Style="{StaticResource CypherButton}"
                            MinWidth="88" Margin="10,0,0,0" Background="#173B3A" BorderBrush="#3FAE9C"
                            VerticalAlignment="Bottom"/>
                </Grid>
            </Border>

            <Grid Grid.Row="4">
                <Grid.ColumnDefinitions>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="Auto"/>
                    <ColumnDefinition Width="*"/>
                    <ColumnDefinition Width="Auto"/>
                </Grid.ColumnDefinitions>
                <Button x:Name="NewChatButton" Grid.Column="0" Content="NEW CHAT" Style="{StaticResource CypherButton}"
                        Padding="12,6" FontSize="11" Background="Transparent"/>
                <Button x:Name="CopyButton" Grid.Column="1" Content="COPY" Style="{StaticResource CypherButton}"
                        Padding="12,6" FontSize="11" Background="Transparent" Margin="8,0,0,0"/>
                <TextBlock Grid.Column="3" Text="LOCAL / PRIVATE / APPROVALS ENFORCED" Foreground="#607783"
                           FontSize="10" VerticalAlignment="Center"/>
            </Grid>
        </Grid>
    </Border>
</Window>
'@

    $script:assistantWindow = [Windows.Markup.XamlReader]::Parse($xaml)
    $script:assistantTitle = $script:assistantWindow.FindName('AssistantTitle')
    $script:assistantStatus = $script:assistantWindow.FindName('StatusText')
    $script:assistantStatusDot = $script:assistantWindow.FindName('StatusDot')
    $script:assistantProgress = $script:assistantWindow.FindName('Progress')
    $script:assistantResponse = $script:assistantWindow.FindName('ResponseBox')
    $script:assistantInput = $script:assistantWindow.FindName('InputBox')
    $script:assistantSend = $script:assistantWindow.FindName('SendButton')
    $script:assistantNewChat = $script:assistantWindow.FindName('NewChatButton')
    $script:assistantCopy = $script:assistantWindow.FindName('CopyButton')
    $script:assistantClose = $script:assistantWindow.FindName('CloseButton')
    $script:assistantTitle.Text = $assistantName.ToUpperInvariant()
    $script:assistantWindow.Title = $assistantName

    [Windows.Forms.Integration.ElementHost]::EnableModelessKeyboardInterop($script:assistantWindow)
    $titleBar = $script:assistantWindow.FindName('TitleBar')
    $titleBar.Add_MouseLeftButtonDown({
        param($sender, $eventArgs)
        if ($eventArgs.LeftButton -eq [Windows.Input.MouseButtonState]::Pressed) {
            try { $script:assistantWindow.DragMove() } catch { }
        }
    })
    $script:assistantClose.Add_Click({ $script:assistantWindow.Hide() })
    $script:assistantCopy.Add_Click({
        if (-not [string]::IsNullOrWhiteSpace($script:lastResponseText)) {
            [Windows.Clipboard]::SetText($script:lastResponseText)
        }
    })
    $script:assistantSend.Add_Click({
        if ($script:submitAssistantRequest) {
            & $script:submitAssistantRequest
        }
    })
    $script:assistantNewChat.Add_Click({
        if ($script:newConversationAction) {
            & $script:newConversationAction
        }
    })
    $script:assistantInput.Add_PreviewKeyDown({
        param($sender, $eventArgs)
        $shiftDown = ([Windows.Input.Keyboard]::Modifiers -band [Windows.Input.ModifierKeys]::Shift) -ne 0
        if ($eventArgs.Key -eq [Windows.Input.Key]::Return -and -not $shiftDown) {
            $eventArgs.Handled = $true
            if ($script:submitAssistantRequest) {
                & $script:submitAssistantRequest
            }
        }
    })
    $script:assistantWindow.Add_PreviewKeyDown({
        param($sender, $eventArgs)
        if ($eventArgs.Key -eq [Windows.Input.Key]::Escape) {
            $eventArgs.Handled = $true
            $script:assistantWindow.Hide()
        }
    })
    $script:assistantWindow.Add_Closing({
        param($sender, $eventArgs)
        if (-not $script:closing) {
            $eventArgs.Cancel = $true
            $sender.Hide()
        }
    })

    Set-CypherResponseText -Text ""
    Set-CypherStatus -Text 'Ready'
}

function Show-CypherWindow {
    Initialize-CypherWindow
    if (-not $script:assistantWindow.IsVisible) {
        $script:assistantWindow.Show()
    }
    if ($script:assistantWindow.WindowState -eq [Windows.WindowState]::Minimized) {
        $script:assistantWindow.WindowState = [Windows.WindowState]::Normal
    }
    $script:assistantWindow.Activate() | Out-Null
    if ($script:assistantInput.IsEnabled) {
        $script:assistantInput.Focus() | Out-Null
    }
}

function Get-ResponseText {
    param([Parameter(Mandatory = $true)]$ResponseObject)

    $pieces = New-Object System.Collections.Generic.List[string]
    foreach ($item in @($ResponseObject.output)) {
        if ([string]$item.type -ne "message" -or [string]$item.role -ne "assistant") {
            continue
        }
        foreach ($part in @($item.content)) {
            if ([string]$part.type -eq "output_text" -and -not [string]::IsNullOrWhiteSpace([string]$part.text)) {
                $pieces.Add([string]$part.text)
            }
        }
    }
    if ($pieces.Count -gt 0) {
        return ($pieces -join [Environment]::NewLine)
    }
    if (-not [string]::IsNullOrWhiteSpace([string]$ResponseObject.output_text)) {
        return [string]$ResponseObject.output_text
    }
    return "Hermes completed the request but returned no displayable text."
}

$createdNew = $false
# Keep the v0.6.1 mutex name so an in-place upgrade cannot run two resident hosts.
$mutex = New-Object System.Threading.Mutex($true, "Local\LocalAssistantHostResidentV061", [ref]$createdNew)
if (-not $createdNew) {
    exit 0
}

$apiKey = $null
$httpClient = $null
$notifyIcon = $null
$hotkeyForm = $null
$heartbeatTimer = $null
$requestTimer = $null
$stopTimer = $null
$requestContent = $null
$httpTask = $null
$requestStarted = $null
$paused = $false
$closing = $false
$assistantWindow = $null
$assistantTitle = $null
$assistantStatus = $null
$assistantStatusDot = $null
$assistantProgress = $null
$assistantResponse = $null
$assistantInput = $null
$assistantSend = $null
$assistantNewChat = $null
$assistantCopy = $null
$assistantClose = $null
$lastResponseText = ""
$submitAssistantRequest = $null
$newConversationAction = $null

try {
    Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
    Write-HostEvent -Event "host_start"
    Ensure-LocalRuntime

    $apiKey = Get-PlaintextSecret -Path $tokenPath
    $httpClient = New-Object System.Net.Http.HttpClient
    $httpClient.Timeout = [TimeSpan]::FromMinutes(30)
    $httpClient.DefaultRequestHeaders.Authorization =
        New-Object System.Net.Http.Headers.AuthenticationHeaderValue("Bearer", $apiKey)

    $hotkeyForm = New-Object ResidentAssistantHotkeyForm
    $null = $hotkeyForm.Handle

    $menu = New-Object System.Windows.Forms.ContextMenuStrip
    $openItem = $menu.Items.Add("Open assistant (Ctrl+Alt+Space)")
    $statusItem = $menu.Items.Add("Status")
    $newConversationItem = $menu.Items.Add("Start new conversation")
    $pauseItem = $menu.Items.Add("Pause activation")
    $pauseItem.CheckOnClick = $true
    $null = $menu.Items.Add("-")
    $exitItem = $menu.Items.Add("Exit until next sign-in")

    $notifyIcon = New-Object System.Windows.Forms.NotifyIcon
    $notifyIcon.Icon = [Drawing.SystemIcons]::Application
    $notifyIcon.Text = "$assistantName local assistant"
    $notifyIcon.ContextMenuStrip = $menu
    $notifyIcon.Visible = $true

    $requestTimer = New-Object System.Windows.Forms.Timer
    $requestTimer.Interval = 250
    $requestTimer.Add_Tick({
        if (-not $script:httpTask -or -not $script:httpTask.IsCompleted) {
            return
        }
        $requestTimer.Stop()
        $elapsed = [int](([DateTime]::UtcNow - $script:requestStarted).TotalMilliseconds)
        $response = $null
        try {
            $response = $script:httpTask.GetAwaiter().GetResult()
            $body = $response.Content.ReadAsStringAsync().GetAwaiter().GetResult()
            if (-not $response.IsSuccessStatusCode) {
                throw "Hermes returned HTTP $([int]$response.StatusCode): $body"
            }
            $parsed = $body | ConvertFrom-Json
            $answer = Get-ResponseText -ResponseObject $parsed
            Write-HostEvent -Event "request_complete" -DurationMs $elapsed
            Set-CypherResponseText -Text $answer
            Set-CypherStatus -Text 'Ready'
            Show-CypherWindow
            $notifyIcon.Text = "$assistantName local assistant"
        } catch {
            Write-HostEvent -Event "request_complete" -Outcome "failed" -DurationMs $elapsed
            Set-CypherResponseText -Text "# Request failed`n`n$($_.Exception.Message)"
            Set-CypherStatus -Text 'Error' -Color '#FF7D88'
            Show-CypherWindow
            $notifyIcon.Text = "$assistantName local assistant - error"
        } finally {
            if ($response) {
                $response.Dispose()
            }
            if ($script:requestContent) {
                $script:requestContent.Dispose()
            }
            $script:requestContent = $null
            $script:httpTask = $null
            $script:requestStarted = $null
        }
    })

    $newConversationAction = {
        if ($script:httpTask) {
            $notifyIcon.ShowBalloonTip(2500, $assistantName, "Wait for the current request to finish first.", [Windows.Forms.ToolTipIcon]::Info)
            return
        }
        $script:conversation = "resident-" + [Guid]::NewGuid().ToString("N")
        $settings.conversation = $script:conversation
        [IO.File]::WriteAllText($configPath, ($settings | ConvertTo-Json -Depth 8), $utf8NoBom)
        Write-HostEvent -Event "conversation_rotated"
        Set-CypherResponseText -Text "# New conversation`n`nA fresh local conversation is ready. Older Hermes history has not been deleted."
        Set-CypherStatus -Text 'Ready'
        Show-CypherWindow
    }

    $submitAssistantRequest = {
        if ($script:paused) {
            $notifyIcon.ShowBalloonTip(2500, $assistantName, "Activation is paused from the tray menu.", [Windows.Forms.ToolTipIcon]::Info)
            return
        }
        if ($script:httpTask) {
            $notifyIcon.ShowBalloonTip(2500, $assistantName, "I am still working on the previous request.", [Windows.Forms.ToolTipIcon]::Info)
            return
        }
        $commandText = [string]$script:assistantInput.Text
        $commandText = $commandText.Trim()
        if ([string]::IsNullOrWhiteSpace($commandText)) {
            return
        }
        if ($commandText.Length -gt 8000) {
            [Windows.Forms.MessageBox]::Show("Commands are limited to 8,000 characters.", $assistantName) | Out-Null
            return
        }

        try {
            Set-CypherResponseText -Text "Working on your request..."
            Set-CypherStatus -Text 'Thinking' -Color '#58CFF5' -Busy $true
            Ensure-LocalRuntime
            $payload = [ordered]@{
                model = "hermes-agent"
                input = $commandText
                instructions = "Act as the user's private local Windows assistant. Follow the configured Hermes tool boundaries. Never claim an action succeeded without a confirming tool result. Never bypass approval requirements."
                conversation = $script:conversation
                store = $true
            } | ConvertTo-Json -Depth 8 -Compress
            $script:requestContent = New-Object System.Net.Http.StringContent(
                $payload,
                [Text.Encoding]::UTF8,
                "application/json"
            )
            $script:requestStarted = [DateTime]::UtcNow
            $script:httpTask = $httpClient.PostAsync(
                $endpoint.TrimEnd("/") + "/v1/responses",
                $script:requestContent
            )
            Write-HostEvent -Event "request_start"
            $notifyIcon.Text = "$assistantName is working"
            $script:assistantInput.Text = ""
            $requestTimer.Start()
        } catch {
            if ($script:requestContent) {
                $script:requestContent.Dispose()
            }
            $script:requestContent = $null
            $script:httpTask = $null
            $script:requestStarted = $null
            Write-HostEvent -Event "request_start" -Outcome "failed"
            Set-CypherResponseText -Text "# Cannot start request`n`n$($_.Exception.Message)"
            Set-CypherStatus -Text 'Error' -Color '#FF7D88'
            Show-CypherWindow
        }
    }

    $invokeAssistant = {
        if ($script:paused) {
            $notifyIcon.ShowBalloonTip(2500, $assistantName, "Activation is paused from the tray menu.", [Windows.Forms.ToolTipIcon]::Info)
            return
        }
        Show-CypherWindow
        if ($script:httpTask) {
            Set-CypherStatus -Text 'Thinking' -Color '#58CFF5' -Busy $true
        }
    }

    $hotkeyForm.add_HotkeyPressed($invokeAssistant)
    $openItem.Add_Click($invokeAssistant)
    $notifyIcon.Add_DoubleClick($invokeAssistant)

    $statusItem.Add_Click({
        $state = if ($script:paused) { "Paused" } elseif ($script:httpTask) { "Working" } else { "Ready" }
        Show-CypherWindow
        Set-CypherResponseText -Text "# $assistantName status`n`n- State: $state`n- Activation: Ctrl+Alt+Space`n- Model: local Hermes + Ollama`n- Network: loopback only`n- Microphone: disabled`n- Host content logging: disabled"
        if ($script:paused) {
            Set-CypherStatus -Text 'Paused' -Color '#F3C969'
        } elseif ($script:httpTask) {
            Set-CypherStatus -Text 'Thinking' -Color '#58CFF5' -Busy $true
        } else {
            Set-CypherStatus -Text 'Ready'
        }
    })

    $newConversationItem.Add_Click($newConversationAction)

    $pauseItem.Add_Click({
        $script:paused = $pauseItem.Checked
        if ($script:paused) {
            $pauseItem.Text = "Resume activation"
            $notifyIcon.Text = "$assistantName local assistant - paused"
            if ($script:assistantWindow) {
                Set-CypherStatus -Text 'Paused' -Color '#F3C969'
            }
            Write-HostEvent -Event "activation_paused"
        } else {
            $pauseItem.Text = "Pause activation"
            $notifyIcon.Text = "$assistantName local assistant"
            if ($script:assistantWindow) {
                Set-CypherStatus -Text 'Ready'
            }
            Write-HostEvent -Event "activation_resumed"
        }
    })

    $exitItem.Add_Click({
        $script:closing = $true
        $hotkeyForm.Close()
    })

    $heartbeatTimer = New-Object System.Windows.Forms.Timer
    $heartbeatTimer.Interval = 5000
    $heartbeatTimer.Add_Tick({
        try {
            $heartbeat = [ordered]@{
                timestamp = [DateTimeOffset]::UtcNow.ToString("o")
                pid = $PID
                status = if ($script:paused) { "paused" } elseif ($script:httpTask) { "working" } else { "ready" }
                version = "0.6.3"
            } | ConvertTo-Json -Compress
            [IO.File]::WriteAllText($heartbeatPath, $heartbeat, $utf8NoBom)
        } catch {
        }
    })
    $heartbeatTimer.Start()

    $stopTimer = New-Object System.Windows.Forms.Timer
    $stopTimer.Interval = 1000
    $stopTimer.Add_Tick({
        if (Test-Path -LiteralPath $stopRequestPath -PathType Leaf) {
            Remove-Item -LiteralPath $stopRequestPath -Force -ErrorAction SilentlyContinue
            $script:closing = $true
            $hotkeyForm.Close()
        }
    })
    $stopTimer.Start()

    if (-not $hotkeyForm.RegistrationSucceeded) {
        Write-HostEvent -Event "hotkey_registration" -Outcome "failed"
        $notifyIcon.ShowBalloonTip(5000, $assistantName, "Ctrl+Alt+Space is already in use. Open me from the tray icon instead.", [Windows.Forms.ToolTipIcon]::Warning)
    } else {
        Write-HostEvent -Event "hotkey_registration"
        $notifyIcon.ShowBalloonTip(3500, $assistantName, "Ready. Press Ctrl+Alt+Space to open the Cypher interface.", [Windows.Forms.ToolTipIcon]::Info)
    }

    [Windows.Forms.Application]::Run($hotkeyForm)
} catch {
    Write-HostEvent -Event "host_failure" -Outcome "failed"
    [Windows.Forms.MessageBox]::Show(
        $_.Exception.Message,
        "$assistantName - Resident host failed",
        [Windows.Forms.MessageBoxButtons]::OK,
        [Windows.Forms.MessageBoxIcon]::Error
    ) | Out-Null
} finally {
    if ($heartbeatTimer) { $heartbeatTimer.Stop(); $heartbeatTimer.Dispose() }
    if ($requestTimer) { $requestTimer.Stop(); $requestTimer.Dispose() }
    if ($stopTimer) { $stopTimer.Stop(); $stopTimer.Dispose() }
    if ($requestContent) { $requestContent.Dispose() }
    if ($httpClient) { $httpClient.Dispose() }
    if ($notifyIcon) { $notifyIcon.Visible = $false; $notifyIcon.Dispose() }
    if ($assistantWindow) {
        $closing = $true
        $assistantWindow.Close()
    }
    if ($hotkeyForm) { $hotkeyForm.Dispose() }
    Remove-Item -LiteralPath $heartbeatPath -Force -ErrorAction SilentlyContinue
    Write-HostEvent -Event "host_stop"
    if ($createdNew) {
        try { $mutex.ReleaseMutex() } catch { }
    }
    $mutex.Dispose()
}

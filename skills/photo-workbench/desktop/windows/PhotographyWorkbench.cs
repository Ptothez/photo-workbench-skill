using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Runtime.InteropServices;
using System.Threading;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

internal class PhotographyWorkbench : Form {
    static int Port=8932;
    static string Url {get{return "http://127.0.0.1:"+Port+"/";}}
    static string AppId;
    readonly WebView2 web=new WebView2();
    readonly Label status=new Label();
    readonly System.Windows.Forms.Timer timer=new System.Windows.Forms.Timer();
    readonly string project;
    readonly string logs;
    Process service;
    bool checking=false,disconnected=false;
    [DllImport("shell32.dll",CharSet=CharSet.Unicode)]static extern int SetCurrentProcessExplicitAppUserModelID(string id);
    [DllImport("user32.dll")]static extern bool SetForegroundWindow(IntPtr handle);
    [DllImport("user32.dll")]static extern bool ShowWindow(IntPtr handle,int command);

    [STAThread]static void Main(){
        string root=Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","..",".."));
        string portFile=Path.Combine(root,"desktop-port.txt");if(File.Exists(portFile)&&(!int.TryParse(File.ReadAllText(portFile).Trim(),out Port)||Port<1024||Port>65535))throw new InvalidOperationException("桌面端口配置无效。");
        using(var sha=System.Security.Cryptography.SHA256.Create())AppId="Photography.Workbench."+BitConverter.ToString(sha.ComputeHash(System.Text.Encoding.UTF8.GetBytes(root.ToUpperInvariant()))).Replace("-","").Substring(0,16);
        SetCurrentProcessExplicitAppUserModelID(AppId);
        bool created;
        using(var mutex=new Mutex(true,"Local\\"+AppId,out created)){
            if(!created){foreach(var process in Process.GetProcessesByName("PhotographyWorkbench")){if(process.Id==Process.GetCurrentProcess().Id||process.MainWindowHandle==IntPtr.Zero)continue;try{if(!string.Equals(process.MainModule.FileName,Process.GetCurrentProcess().MainModule.FileName,StringComparison.OrdinalIgnoreCase))continue;}catch{continue;}ShowWindow(process.MainWindowHandle,9);SetForegroundWindow(process.MainWindowHandle);return;}return;}
            Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
            try{Application.Run(new PhotographyWorkbench());}catch(Exception ex){MessageBox.Show(ex.Message,"摄影工作台启动失败");}
        }
    }
    PhotographyWorkbench(){
        project=Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory,"..","..",".."));
        logs=Path.Combine(project,"data","runtime");Directory.CreateDirectory(logs);
        Text="摄影工作台";Icon=new Icon(Path.Combine(project,"assets","photo-icon.ico"));
        MinimumSize=new Size(1024,720);Size=new Size(1440,960);StartPosition=FormStartPosition.CenterScreen;
        web.Dock=DockStyle.Fill;status.Dock=DockStyle.Bottom;status.Height=30;status.Padding=new Padding(12,4,0,0);status.BackColor=Color.FromArgb(244,244,236);status.Text="正在启动摄影工作台…";
        Controls.Add(web);Controls.Add(status);Shown+=async (sender,args)=>await Start();
        timer.Interval=10000;timer.Tick+=async (sender,args)=>await Check();
        FormClosed+=(sender,args)=>{timer.Stop();if(service!=null){try{if(!service.HasExited)service.Kill();}catch{}service.Dispose();}};
    }
    async Task<bool> Healthy(){
        try{var request=(HttpWebRequest)WebRequest.Create(Url+"api/health");request.Timeout=2000;request.ReadWriteTimeout=2000;using(var response=await request.GetResponseAsync())using(var reader=new StreamReader(response.GetResponseStream())){string text=await reader.ReadToEndAsync();return (text.Contains("\"version\": 2")||text.Contains("\"version\":2"))&&text.Contains(AppId.Substring("Photography.Workbench.".Length));}}catch{return false;}
    }
    async Task EnsureService(){
        if(await Healthy())return;
        try{var request=(HttpWebRequest)WebRequest.Create(Url+"api/health");request.Timeout=1000;using(var response=await request.GetResponseAsync()){throw new InvalidOperationException("本机端口正在运行其他版本。请先由 Agent 核对，未强行停止任何进程。");}}catch(WebException ex){if(ex.Response!=null)throw new InvalidOperationException("本机端口已被其他服务占用。");}
        if(service!=null&&!service.HasExited) return;
        string python=null;foreach(string folder in (Environment.GetEnvironmentVariable("PATH")??"").Split(';')){string f=Path.Combine(folder.Trim('"'),"python.exe");if(File.Exists(f)&&!f.Contains("WindowsApps")){python=f;break;}}
        if(python==null)throw new FileNotFoundException("找不到可用的 Python。请由 Agent 检查本机运行环境。");
        var info=new ProcessStartInfo(python,"-X utf8 -u \""+Path.Combine(project,"start.py")+"\" --port "+Port+"");
        info.WorkingDirectory=project;info.UseShellExecute=false;info.CreateNoWindow=true;info.RedirectStandardOutput=true;info.RedirectStandardError=true;info.StandardOutputEncoding=System.Text.Encoding.UTF8;info.StandardErrorEncoding=System.Text.Encoding.UTF8;
        service=new Process();service.StartInfo=info;service.OutputDataReceived+=(sender,args)=>Log(args.Data);service.ErrorDataReceived+=(sender,args)=>Log(args.Data);service.Start();service.BeginOutputReadLine();service.BeginErrorReadLine();
        for(int i=0;i<40;i++){if(await Healthy())return;if(service.HasExited)throw new InvalidOperationException("本地服务启动失败，详情已保存在运行记录中。");await Task.Delay(250);}
        throw new TimeoutException("本地服务尚未就绪，详情已保存在运行记录中。");
    }
    readonly object logLock=new object();
    void Log(string message){if(message==null)return;try{lock(logLock)File.AppendAllText(Path.Combine(logs,"desktop-service.log"),DateTime.Now.ToString("s")+" "+message+Environment.NewLine);}catch{}}
    async Task Start(){
        try{
            await EnsureService();
            var env=await CoreWebView2Environment.CreateAsync(null,Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),AppId,"WebView2"));
            await web.EnsureCoreWebView2Async(env);
            web.CoreWebView2.Settings.AreDevToolsEnabled=false;web.CoreWebView2.Settings.AreDefaultContextMenusEnabled=false;
            web.CoreWebView2.NavigationStarting+=(sender,args)=>{Uri uri;if(Uri.TryCreate(args.Uri,UriKind.Absolute,out uri)&&uri.Scheme!="about"&&(uri.Host!="127.0.0.1"||uri.Port!=Port))args.Cancel=true;};
            web.CoreWebView2.NewWindowRequested+=(sender,args)=>{args.Handled=true;Uri uri;if(Uri.TryCreate(args.Uri,UriKind.Absolute,out uri)&&uri.Host=="127.0.0.1"&&uri.Port==Port)web.CoreWebView2.Navigate(args.Uri);};
            web.CoreWebView2.Navigate(Url);status.Text="摄影工作台 · 本机服务已连接";timer.Start();
        }catch(Exception ex){Log(ex.ToString());status.Text="启动未完成："+ex.Message;MessageBox.Show(ex.Message+"\n运行记录："+logs,"摄影工作台");}
    }
    async Task Check(){
        if(checking)return;checking=true;
        try{if(!await Healthy()){disconnected=true;status.Text="连接中断，正在恢复本地服务；尚未保存的意见请保留。";await EnsureService();}if(disconnected){web.Reload();disconnected=false;}status.Text="摄影工作台 · 本机服务已连接";}catch(Exception ex){status.Text="连接尚未恢复："+ex.Message;Log(ex.Message);}finally{checking=false;}
    }
}

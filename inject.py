import os

POSTHOG_SNIPPET = '''
<!-- PostHog -->
<script>
  !function(t,e){var o,n,p,r;e.__SV=1,(t.posthog=e.posthog||[]).init=function(i,s,a){
    function c(t,e){var o=e.split(".");2==o.length&&(t=t[o[0]],e=o[1]),
      t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}} 
    p=e.createElement("script"),p.type="text/javascript",p.async=!0,
    p.src="https://app.posthog.com/static/array.js",r=e.getElementsByTagName("script")[0],r.parentNode.insertBefore(p,r);
    var u=e.posthog;u._i=[];u.init=function(t,e,o){function n(t,e){var o=e.split(".");
      2==o.length&&(t=t[o[0]],e=o[1]),t[e]=function(){t.push([e].concat(Array.prototype.slice.call(arguments,0)))}} 
      var p=u;void 0!==o?p=u[o]=[]:o="posthog";p.people=p.people||[];p.toString=function(t){var e="posthog";
      return"posthog"!==o&&(e+="."+o),t||(e+=" (stub)"),e};p.people.toString=function(){return p.toString(1)+".people (stub)"};
      var r="capture identify alias people.set people.set_once people.unset reset group".split(" ");
      for(var i=0;i<r.length;i++)n(p,r[i]);u._i.push([t,e,o])};
    e.posthog.init(i,s,a)
  }(document,window);
  posthog.init('REPLACE_ME_POSTHOG_KEY',{api_host:'https://app.posthog.com'});
</script>
'''

HOTJAR_SNIPPET = '''
<!-- Hotjar -->
<script>
  (function(h,o,t,j,a,r){
    h.hj=h.hj||function(){(h.hj.q=h.hj.q||[]).push(arguments)};
    h._hjSettings={hjid: 'REPLACE_ME_HOTJAR_ID', hjsv: 6};
    a=o.getElementsByTagName('head')[0];
    r=o.createElement('script');r.async=1;r.src=t+h._hjSettings.hjid+j+h._hjSettings.hjsv;
    a.appendChild(r);
  })(window,document,'https://static.hotjar.com/c/hotjar-','.js?sv=');
</script>
'''

WORKSPACE_TRACKING = '''
<script>
  document.addEventListener('DOMContentLoaded', () => {
    if (window.posthog) {
      window.posthog.capture('workspace_opened');
    }
  });
</script>
'''

LANDING_TRACKING = '''
<script>
  document.addEventListener('DOMContentLoaded', () => {
    const btns = document.querySelectorAll('a, button');
    btns.forEach(btn => {
      if (btn.innerText && btn.innerText.match(/Demo|Get Started/i)) {
        btn.addEventListener('click', () => {
          if (window.posthog) window.posthog.capture('cta:demo_clicked');
        });
      }
    });
  });
</script>
'''

AUTH_TRACKING = '''
<script>
  document.addEventListener('DOMContentLoaded', () => {
    const btns = document.querySelectorAll('a, button');
    btns.forEach(btn => {
      if (btn.innerText && btn.innerText.match(/Login|Sign Up/i)) {
        btn.addEventListener('click', () => {
          if (window.posthog) window.posthog.capture('signup_submitted', { method: 'email' });
        });
      }
    });
  });
</script>
'''

def inject(path, is_landing=False, is_auth=False, is_workspace=False):
    if not os.path.exists(path):
        print(f"Skipping {path}, not found.")
        return
        
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
        
    if "REPLACE_ME_POSTHOG_KEY" in content:
        print(f"Skipping {path}, already injected.")
        return
        
    insertion = POSTHOG_SNIPPET
    
    if is_landing or is_auth:
        insertion += HOTJAR_SNIPPET
        
    if is_landing:
        insertion += LANDING_TRACKING
    elif is_auth:
        insertion += AUTH_TRACKING
    elif is_workspace:
        insertion += WORKSPACE_TRACKING
        
    content = content.replace("</head>", insertion + "</head>")
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Injected into {path}")

# Run injections
inject('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/landing/index.html', is_landing=True)
inject('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/static/auth.html', is_auth=True)
inject('C:/Users/antho/.windsurf/veklom-byos-backend/frontend/static/workspace/index.html', is_workspace=True)

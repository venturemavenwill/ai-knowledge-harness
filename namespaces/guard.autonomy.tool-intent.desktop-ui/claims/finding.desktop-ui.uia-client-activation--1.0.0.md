<!-- aikb
{
  "schema_version": 1,
  "claim_id": "finding.desktop-ui.uia-client-activation",
  "namespace": "guard.autonomy.tool-intent.desktop-ui",
  "version": "1.0.0",
  "expression": "On Windows 11 25H2 with a .NET 8 WPF window that is designed never to activate, every UI Automation pattern action issued through the managed System.Windows.Automation client activated the target window, because the provider received a UI Automation focus request before the action; the same actions issued through the native COM IUIAutomation client delivered their effects with no activation and no focus request.",
  "authority": "primary-measurement",
  "scope": {
    "holds_when": "choosing or debugging a UI Automation client for agent actions on Windows, specifically for WPF providers; other UI frameworks and other Windows builds were not measured",
    "expires": null
  },
  "confidence": null,
  "confidence_method": "single-machine controlled experiment: isolated per-action probes on freshly launched test-owned windows, in-target window-message and managed-stack logging, a no-pattern-call control, an alternate-parent launch control, and two independent repetitions per client; no numeric confidence across machines or frameworks",
  "provenance": {
    "producer": "assistant-measurement://operator-authorized",
    "producer_version": "1.0.0",
    "authored_utc": "2026-10-08",
    "derived_from": [
      {
        "source": "assistant-session",
        "locator": "2026-10-08 live probes on Microsoft Windows 11 Enterprise 10.0.26200 (25H2), Microsoft.WindowsDesktop.App 8.0.31; target: WPF window with ShowActivated=false, WS_EX_NOACTIVATE, WS_EX_TOOLWINDOW, launched as a child process and separately via explorer.exe; Visual Studio Code held the foreground before each action",
        "evidence_class": "primary-result"
      },
      {
        "source": "https://github.com/dotnet/wpf/blob/c52e465d3c50c526dabd6259365624a814f58432/src/Microsoft.DotNet.Wpf/src/UIAutomation/UIAutomationClient/System/Windows/Automation/InvokePattern.cs",
        "locator": "managed InvokePattern.Invoke calls only UiaCoreApi.InvokePattern_Invoke",
        "evidence_class": "design-reference"
      },
      {
        "source": "https://github.com/dotnet/wpf/blob/main/src/Microsoft.DotNet.Wpf/src/PresentationCore/MS/internal/Automation/ElementProxy.cs",
        "locator": "ElementProxy.SetFocus (provider SetFocus entry point) dispatches InContextSetFocus, which calls AutomationPeer.SetFocus",
        "evidence_class": "design-reference"
      }
    ]
  },
  "lineage": {
    "status": "active",
    "generation": 1,
    "parent_refs": []
  },
  "relationships": [
    {
      "kind": "informs",
      "target": "spec.guard.autonomy.tool-intent.desktop-ui@1.0.0"
    },
    {
      "kind": "applies",
      "target": "engineering.repair.root-cause"
    }
  ],
  "retrieval": {
    "tags": [
      "computer-use",
      "desktop-automation",
      "focus-stealing",
      "foreground-window",
      "ui-automation",
      "uiautomationclient",
      "windows",
      "wpf"
    ]
  }
}
-->

# Managed UI Automation client activates WPF targets; COM IUIAutomation did not

## Activation

Consult this finding when an agent tool performs UI Automation actions on
Windows and must not disturb the window the user is working in. It does not
cover synthetic keyboard or mouse input, which always targets the foreground,
or UI frameworks other than WPF.

## Finding

A UI Automation pattern call is often described as "focus-free" because no
synthetic input is sent. That description depends on the **client library**.

### Measured results

Each probe launched a fresh, test-owned WPF window that was configured never to
activate. The probe confirmed the window was not the foreground, performed
exactly one action, then reread the foreground window after 250 ms.

| Action | Managed `System.Windows.Automation` | Native COM `IUIAutomation` (2 runs) |
|---|---|---|
| `InvokePattern.Invoke` | Activated (3 of 3, including an explorer-launched window) | No activation; click delivered |
| `TogglePattern.Toggle` | Activated | No activation; state verified |
| `ValuePattern.SetValue` | Activated (also explorer-launched) | No activation; value verified |
| `ExpandCollapsePattern.Expand` | Activated | No activation; state verified |
| `ExpandCollapsePattern.Collapse` | Activated | No activation; state verified |
| `SelectionItemPattern.Select` | Activated | No activation; state verified |

A separate Python `comtypes` COM client also delivered `Invoke` with no
activation in 3 of 3 runs.

### Mechanism evidence

The target logged window messages and WPF focus events with managed stacks.

1. For every managed-client action, the order was: activating
   `WM_WINDOWPOSCHANGING`, then `WM_ACTIVATE`, then a WPF focus change through
   `ElementProxy.InContextSetFocus`, `AutomationPeer.SetFocus`, and
   `UIElement.Focus`, and only then the control's own event, such as
   `Button.Click` or `TextChanged`.
2. `ElementProxy.SetFocus` is WPF's provider-side implementation of the UI
   Automation focus request. WPF pattern code does not call it, so the request
   originated on the client side.
3. **Control 1:** the full action path without the pattern method call
   (window checks, `FindFirst`, property reads, pattern lookup) caused no
   activation.
4. **Control 2:** a target launched through `explorer.exe`, so it inherited no
   foreground rights from the agent's process tree, activated the same way.
   Inherited launch rights therefore do not explain the effect.
5. With the COM client, the target logged no activation messages and no focus
   events at all.

### Uncertainty

- The point inside the managed client's flat-API path where the focus request
  is issued was inferred from client and provider evidence, not traced in
  UI Automation Core.
- Only one machine, one Windows build, and WPF providers were measured. Win32,
  WinUI, UWP, Electron, and Qt providers may behave differently in either
  direction.
- Applications can still activate themselves in response to a correctly
  delivered action. Client choice removes one cause, not every cause.

## Procedure implication

- Do not describe managed `System.Windows.Automation` pattern calls as
  non-activating.
- Prefer the native COM `IUIAutomation` interface for actions. Declare only
  the methods used, take vtable order from the Windows SDK
  `UIAutomationClient.h`, and do not bind the element focus method.
- Treat client choice as necessary but not sufficient. Each application and
  action still requires its own probe under
  `spec.guard.autonomy.tool-intent.desktop-ui`.
- When reading control types from COM, map `UIA_*ControlTypeId` values with an
  explicit table. In the measured process, `ControlType.LookupById` returned
  null before the managed control-type table was initialized. That made every
  identity check fail closed.

## Verification

Launch a non-activating WPF window owned by the test, with the foreground held
by another application. Perform one pattern action through each client and
compare `GetForegroundWindow` before and after. Log `WM_ACTIVATE` and WPF
`GotKeyboardFocus` stacks in the target.

**Falsified if:** on the scoped configuration, a managed-client pattern call
completes without a provider focus request or activation, or a COM-client
pattern call produces one.

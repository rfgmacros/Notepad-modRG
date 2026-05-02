# Notepad-modRG

A Claude-developed modification of macOS Notepad++, focusing on macOS UI elements. The original source is here:

https://github.com/rfgmacros/Notepad-modRG

And as I'm not a coder, everything here was written by Claude, so it's probably janky as heck, but it works for me, which is all I wanted. Here's what's changed in this version:

- Converted the entire thing into an Xcode project, so I could work with Claude within Xcode.
- Moved Settings > Preferences to a real Settings menu (under the app name menu), and the other items were moved to the Tools menu.
- Updated the layout of Settings to match macOS standards.
- Sped up the loading of the Settings page.
- Converted the toolbar to a standard macOS toolbar, where icons can be rearranged or removed, and the Customize Toolbar contextual menu can be used to further modify the toolbar, adding Spaces and Flexible Spaces, etc.
- Added a proxuy icon on the filename in the toolbar, i.e. right-click on the filename to see and select any folder on the path to the saved file.
- Added support for dragging and dropping tabs to rearrange them, both within the current window, and across windows.
- Added Accessibility UI support for the tabs, so they show up in our (manytricks.com) app Witch, and other similar utiltiies.
- Moved the Language and Encoding menus to the window chrome, as pop-up menus.
- Changed the "?" menu item to help, and added the standard macOS command search in the Help menu.

As noted, I wrote none of this code, and it's probably completely bizarre, but it works. Use at your own risk :).


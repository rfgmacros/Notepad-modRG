#import <Cocoa/Cocoa.h>

/// Builds the application's main menu bar programmatically.
@interface MenuBuilder : NSObject
+ (void)buildMainMenu;

/// Insert dynamically-loaded plugin menu items into the Plugins menu.
/// Items are placed before the separator that precedes "Plugins Admin…".
+ (void)insertPluginMenuItems:(NSArray<NSMenuItem *> *)items;

/// The Encoding and Language menus built during +buildMainMenu.
/// These are NOT in the menu bar; they are surfaced via the status-bar
/// popup buttons instead.
+ (NSMenu *)encodingMenu;
+ (NSMenu *)languageMenu;
@end

package widgets.Gameplay.SimInfoHUD.SimInfoTray
{
   import flash.display.DisplayObject;
   import flash.display.MovieClip;
   import flash.events.Event;
   import flash.geom.Point;
   import flash.text.TextField;
   import gamedata.Gameplay.InteractionMenu.InteractionCategory;
   import olympus.constants.ActionCodes;
   import olympus.controls.GUIComponent;
   import olympus.controls.GUIPaginationBar;
   import olympus.core.widget.Margin;
   import olympus.data.SelectableArrayDataFeed;
   import olympus.events.GridEvent;
   import olympus.events.PushButtonEvent;
   import olympus.extensions.InputModeVisibilityExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.NavDirection;
   import olympus.gamepad.NavManager;
   import olympus.gui.buttons.Button;
   import olympus.gui.grids.SelectionGrid;
   import olympus.input.IInputAdapter;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.BidirectionalGroupAdapter;
   import olympus.input.adapters.GridInputAdapter;
   import olympus.input.adapters.InputAdapterConfirmEvent;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.input.adapters.InputAdapterLeaveEvent;
   import olympus.input.adapters.PaginationBarAdapter;
   import olympus.io.CommunicationManager;
   import olympus.layout.GridLayout;
   import olympus.localization.KeysConsole;
   import olympus.localization.KeysGP;
   import olympus.localization.LocKey;
   import olympus.utils.SystemUtils;
   import olympus.utils.TextUtils;
   import olympus.views.GridView;
   import widgets.Gameplay.SimInfoHUD.SimInfoTray.constants.SimInfoTrayTunables;
   import widgets.Gameplay.SimInfoHUD.SimInfoTray.events.PhoneScreenEvent;
   import widgets.shared.controls.Console.LegendIcon;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol131")]
   public class PhoneCategoryScreen extends GUIComponent implements IPhoneScreen, IInputAdapter
   {
      
      public var mcPaginationBar:GUIPaginationBar;
      
      public var mcCategoryName:TextField;
      
      public var mcControllerTabLeft:LegendIcon;
      
      public var mcControllerTabRight:LegendIcon;
      
      public var mcBackgroundHelperClip:MovieClip;
      
      public var mcPhoneBackgroundColorSelector:PhoneBackgroundColorSelector;
      
      public var mcPhoneCaseSelector:PhoneCaseSelector;
      
      public var btnSilence:Button;
      
      public var btnBackgroundColorSelector:Button;
      
      public var btnCaseSelector:Button;
      
      protected var mCategoryGrid:SelectionGrid;
      
      protected var mCategoryFeed:SelectableArrayDataFeed;
      
      protected var mCategoryLayout:GridLayout;
      
      protected var mCategoryPageFeed:PhoneCategoryDataFeed;
      
      protected var mCategoryWidth:Number;
      
      protected var mCategoryInput:GridInputAdapter;
      
      protected var mToolInput:BidirectionalGroupAdapter;
      
      protected var mPaginationInput:PaginationBarAdapter;
      
      protected var mTabRight:InputAction;
      
      protected var mTabLeft:InputAction;
      
      public function PhoneCategoryScreen()
      {
         super();
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.btnSilence.addEventListener(PushButtonEvent.CLICK,this.OnSilenceToolClick,false,0,true);
         this.btnBackgroundColorSelector.addEventListener(PushButtonEvent.CLICK,this.OnBackgroundColorSelectorToolClick,false,0,true);
         this.btnCaseSelector.addEventListener(PushButtonEvent.CLICK,this.OnCaseSelectorToolClick,false,0,true);
         this.btnSilence.Selected = CommunicationManager.CallGameService("GetPhoneSilence") as Boolean;
         this.btnSilence.Toggle = true;
         this.btnBackgroundColorSelector.Toggle = true;
         this.btnCaseSelector.Toggle = true;
         var _loc1_:LocKey = this.btnSilence.Selected ? KeysGP.SIM_INFO_TRAY_PHONE_TOOL_UNSILENCE : KeysGP.SIM_INFO_TRAY_PHONE_TOOL_SILENCE;
         this.btnSilence.TooltipExt.SetText(_loc1_);
         this.btnBackgroundColorSelector.TooltipExt.SetText(KeysGP.SIM_INFO_TRAY_PHONE_TOOL_CHANGE_BG_COLOR);
         this.btnCaseSelector.TooltipExt.SetText(KeysGP.SIM_INFO_TRAY_PHONE_TOOL_CHANGE_CASE_COLOR);
         this.mcPhoneBackgroundColorSelector.Hide();
         this.mcPhoneCaseSelector.Hide();
         var _loc2_:Margin = SimInfoTrayTunables.PHONE_CATEGORY_CELLVIEW_MARGIN;
         var _loc3_:int = SimInfoTrayTunables.PHONE_CATEGORY_GRID_ITEMS_PER_ROW;
         var _loc4_:SelectionGrid = new SelectionGrid();
         var _loc5_:GridView = new GridView();
         _loc4_.addChild(_loc5_);
         _loc4_.mcGridView = _loc5_;
         addChild(_loc4_);
         this.mCategoryFeed = new SelectableArrayDataFeed();
         this.mCategoryLayout = new GridLayout(false,true,_loc3_);
         _loc4_.InitializeSelectionGrid(this.mCategoryFeed,PhoneCategoryCellView,true,_loc2_,this.mCategoryLayout);
         _loc4_.SetSelectionGridListener(PushButtonEvent.CLICK);
         _loc4_.SetGridListener(PushButtonEvent.ROLL_OVER,this.OnPhoneCategoryRollOver);
         _loc4_.SetGridListener(PushButtonEvent.ROLL_OUT,this.OnPhoneCategoryRollOut);
         _loc4_.addEventListener(GridEvent.SELECTION_UPDATE,this.OnPhoneCategoryClick,false,0,true);
         this.mCategoryGrid = _loc4_;
         this.mCategoryWidth = (this.mCategoryLayout.GetCellBounds().width + _loc2_.Horizontal) * _loc3_;
         this.mCategoryPageFeed = new PhoneCategoryDataFeed();
         this.mCategoryPageFeed.addEventListener(Event.CHANGE,this.OnDataFeedChanged,false,0,true);
         InputModeVisibilityExtension.ShowForController(this.mcControllerTabLeft);
         InputModeVisibilityExtension.ShowForController(this.mcControllerTabRight);
         this.mcControllerTabLeft.ActionCode = ActionCodes.TAB_LEFT;
         this.mcControllerTabRight.ActionCode = ActionCodes.TAB_RIGHT;
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
      }
      
      public function SetData(param1:Array, param2:Array, param3:int, param4:Boolean = false) : InteractionCategory
      {
         var _loc5_:int = 0;
         var _loc6_:PhoneCategoryCellView = null;
         this.mCategoryPageFeed.RemoveAllItems();
         this.mCategoryPageFeed.AddItemsFromIterable(param1);
         this.mCategoryPageFeed.CurrentPage = this.mCategoryPageFeed.RequestPageByCategory(param3);
         this.mcPaginationBar.PagingTarget = this.mCategoryPageFeed;
         this.mcPaginationBar.AutoHide = SimInfoTrayTunables.PHONE_PAGINATION_AUTO_HIDE;
         this.mCategoryFeed.RemoveAllItems();
         this.mCategoryFeed.AddItemsFromIterable(this.mCategoryPageFeed.CurrentItem);
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.mCategoryInput.SetHighlightedIndex(this.mCategoryPageFeed.RequestIndexPerPage(param3));
            if(this.mCategoryPageFeed.PageCount <= 1)
            {
               this.mcControllerTabLeft.visible = false;
               this.mcControllerTabRight.visible = false;
            }
            else
            {
               this.mTabLeft.SetLegendKey(KeysConsole.PREVIOUS_PAGE);
               this.mTabRight.SetLegendKey(KeysConsole.NEXT_PAGE);
            }
         }
         this.RefreshLayout();
         if(param4)
         {
            _loc5_ = this.mCategoryPageFeed.RequestIndexPerPage(param3);
            _loc6_ = this.mCategoryLayout.GetViewAtIndex(_loc5_) as PhoneCategoryCellView;
            _loc6_.visible = false;
            this.mcPaginationBar.mouseEnabled = this.mcPaginationBar.mouseChildren = false;
            this.mCategoryGrid.mcGridView.mouseEnabled = this.mCategoryGrid.mcGridView.mouseChildren = false;
         }
         return this.mCategoryPageFeed.RequestItemAt(param3) as InteractionCategory;
      }
      
      public function RefreshUIForCategories(param1:Array) : void
      {
         var _loc2_:InteractionCategory = null;
         var _loc3_:int = 0;
         var _loc4_:PhoneCategoryCellView = null;
         for each(_loc2_ in param1)
         {
            _loc3_ = this.mCategoryFeed.IndexOf(_loc2_);
            if(_loc3_ != -1)
            {
               _loc4_ = this.mCategoryLayout.GetViewAtIndex(_loc3_) as PhoneCategoryCellView;
               _loc4_.mcNotificationBadge.visible = _loc2_.ShouldDisplayNotification();
            }
         }
      }
      
      public function RetrieveCategoryPosition(param1:int) : Point
      {
         var _loc2_:PhoneCategoryCellView = this.mCategoryLayout.GetViewAtIndex(this.mCategoryPageFeed.RequestIndexPerPage(param1)) as PhoneCategoryCellView;
         if(!_loc2_)
         {
            return null;
         }
         return localToGlobal(new Point(_loc2_.x + this.mCategoryGrid.x,_loc2_.y + this.mCategoryGrid.y));
      }
      
      public function OnScreenSwitchComplete(param1:int) : void
      {
         var _loc2_:PhoneCategoryCellView = this.mCategoryLayout.GetViewAtIndex(this.mCategoryPageFeed.RequestIndexPerPage(param1)) as PhoneCategoryCellView;
         if(!_loc2_)
         {
            return;
         }
         _loc2_.visible = true;
         this.mcPaginationBar.mouseEnabled = this.mcPaginationBar.mouseChildren = true;
         this.mCategoryGrid.mcGridView.mouseEnabled = this.mCategoryGrid.mcGridView.mouseChildren = true;
         if(SystemUtils.UsingConsoleInputMode)
         {
            NavManager.Instance.FocusForward(this);
         }
      }
      
      protected function OnPhoneCategoryClick(param1:GridEvent) : void
      {
         var _loc2_:* = undefined;
         if(param1.mCellEvent == null)
         {
            return;
         }
         _loc2_ = this.mCategoryPageFeed.IndexOf(param1.mData as InteractionCategory);
         var _loc3_:Object = {
            "category":_loc2_,
            "screen":PhonePanel.INTERACTION_SCREEN
         };
         (param1.mCellEvent.currentTarget as DisplayObject).visible = false;
         dispatchEvent(new PhoneScreenEvent(PhoneScreenEvent.SWITCH_SCREEN,false,false,_loc3_));
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.Exit();
         }
      }
      
      protected function OnPhoneCategoryRollOver(param1:GridEvent) : void
      {
         var _loc3_:String = null;
         if(param1.mCellEvent == null)
         {
            return;
         }
         var _loc2_:InteractionCategory = param1.mData as InteractionCategory;
         if(_loc2_ != null)
         {
            TextUtils.ResizeTextToFit(this.mcCategoryName,_loc2_.displayText.toString());
            try
            {
               _loc3_ = encodeURIComponent(_loc2_.displayText.toString());
               _loc3_ = _loc3_.split("'").join("%27");
               _loc3_ = _loc3_.split("(").join("%28");
               _loc3_ = _loc3_.split(")").join("%29");
               _loc3_ = _loc3_.split("!").join("%21");
               CommunicationManager.PostServerCommand("a11y.widget_enc",_loc3_);
            }
            catch(e:Error)
            {
            }
         }
      }
      
      protected function OnPhoneCategoryRollOut(param1:GridEvent) : void
      {
         TextUtils.SetAndEllipsizeText(this.mcCategoryName,"");
      }
      
      protected function OnSilenceToolClick(param1:PushButtonEvent) : void
      {
         CommunicationManager.PostServerCommand("ui.toggle_silence_phone");
         var _loc2_:LocKey = this.btnSilence.Selected ? KeysGP.SIM_INFO_TRAY_PHONE_TOOL_UNSILENCE : KeysGP.SIM_INFO_TRAY_PHONE_TOOL_SILENCE;
         this.btnSilence.AudioExt.ElementName = this.btnSilence.Selected ? "PhoneUnsilenceButton" : "PhoneSilenceButton";
         this.btnSilence.TooltipExt.SetText(_loc2_);
      }
      
      protected function OnBackgroundColorSelectorToolClick(param1:PushButtonEvent) : void
      {
         if(this.mcPhoneBackgroundColorSelector.visible)
         {
            this.mcPhoneBackgroundColorSelector.Hide();
         }
         else
         {
            this.mcPhoneBackgroundColorSelector.Show();
            this.RepositionColorSelector(this.mcPhoneBackgroundColorSelector,this.btnBackgroundColorSelector);
         }
      }
      
      protected function OnCaseSelectorToolClick(param1:PushButtonEvent) : void
      {
         if(this.mcPhoneCaseSelector.visible)
         {
            this.mcPhoneCaseSelector.Hide();
         }
         else
         {
            this.mcPhoneCaseSelector.Show();
            this.RepositionColorSelector(this.mcPhoneCaseSelector,this.btnCaseSelector);
         }
      }
      
      protected function OnDataFeedChanged(param1:Event) : void
      {
         this.mCategoryFeed.RemoveAllItems();
         this.mCategoryFeed.AddItemsFromIterable(this.mCategoryPageFeed.CurrentItem);
      }
      
      protected function RepositionColorSelector(param1:DisplayObject, param2:Button) : void
      {
         param1.x = param2.x + 0.5 * (param2.width - param1.width);
         param1.y = -param1.height;
      }
      
      protected function RefreshLayout() : void
      {
         this.mcPhoneBackgroundColorSelector.ToggleComponent = this.btnBackgroundColorSelector;
         this.mcPhoneCaseSelector.ToggleComponent = this.btnCaseSelector;
         var _loc1_:Number = this.btnSilence.y + this.btnSilence.height + SimInfoTrayTunables.PHONE_CATEGORY_GRID_TOP_OFFSET;
         this.mCategoryGrid.x = (this.mcBackgroundHelperClip.width - this.mCategoryWidth) * 0.5;
         this.mCategoryGrid.y = _loc1_;
         this.mCategoryLayout.PositionCells();
         this.mcPaginationBar.x = (this.mcBackgroundHelperClip.width - this.mcPaginationBar.width) * 0.5;
      }
      
      protected function InitGamepad() : void
      {
         this.mCategoryInput = new GridInputAdapter(this.mCategoryLayout);
         this.mCategoryInput.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveCategory);
         this.mToolInput = new BidirectionalGroupAdapter(new <DisplayObject>[this.btnSilence,this.btnBackgroundColorSelector,this.btnCaseSelector],true);
         this.mToolInput.OnInputEventCall(InputAdapterEvent.LEAVE,this.HandleLeaveTool);
         this.mToolInput.OnInputEventCall(InputAdapterEvent.CONFIRM,this.HandleConfirmTool);
         this.mPaginationInput = new PaginationBarAdapter(this.mcPaginationBar);
         this.mPaginationInput.OnLeaveCall(this.HandleLeavePagination);
         this.mTabLeft = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_LEFT)).CallFunction(this.HandlePageLeft);
         this.mTabRight = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.TAB_RIGHT)).CallFunction(this.HandlePageRight);
         this.mCategoryInput.AddInputActions([this.mTabLeft,this.mTabRight]);
         this.mToolInput.AddInputActions([this.mTabLeft,this.mTabRight]);
         this.mPaginationInput.AddInputActions([this.mTabLeft,this.mTabRight]);
      }
      
      protected function HandleLeaveCategory(param1:InputAdapterLeaveEvent) : void
      {
         if(param1.GetDirection() == NavDirection.UP)
         {
            NavManager.Instance.FocusPan(this.mToolInput,param1.CreateEnterParams());
         }
         else if(param1.GetDirection() == NavDirection.DOWN && this.mcPaginationBar.visible)
         {
            NavManager.Instance.FocusPan(this.mPaginationInput,param1.CreateEnterParams());
         }
         else if(param1.GetDirection() == NavDirection.RIGHT)
         {
            this.HandlePageRight(true);
         }
         else if(param1.GetDirection() == NavDirection.LEFT)
         {
            this.HandlePageLeft(true);
         }
      }
      
      protected function HandleConfirmTool(param1:InputAdapterConfirmEvent) : void
      {
         if(param1.GetObj() == this.mcPhoneBackgroundColorSelector.ToggleComponent)
         {
            NavManager.Instance.FocusForward(this.mcPhoneBackgroundColorSelector);
         }
         else if(param1.GetObj() == this.mcPhoneCaseSelector.ToggleComponent)
         {
            NavManager.Instance.FocusForward(this.mcPhoneCaseSelector);
         }
      }
      
      protected function HandleLeaveTool(param1:InputAdapterLeaveEvent) : void
      {
         if(param1.GetDirection() == NavDirection.DOWN)
         {
            NavManager.Instance.FocusPan(this.mCategoryInput,param1.CreateEnterParams());
         }
      }
      
      protected function HandleLeavePagination(param1:InputAdapterLeaveEvent) : void
      {
         if(param1.GetDirection() == NavDirection.UP)
         {
            NavManager.Instance.FocusPan(this.mCategoryInput,param1.CreateEnterParams());
         }
      }
      
      protected function HandlePageLeft(param1:Boolean = false) : void
      {
         var _loc2_:int = -1;
         if(NavManager.Instance.CurrentFocusable == this.mCategoryInput && this.mCategoryPageFeed.CanAdvancePage(-1))
         {
            _loc2_ = this.mCategoryInput.GetHighlightedIndex();
            if(param1)
            {
               _loc2_ += SimInfoTrayTunables.PHONE_CATEGORY_GRID_ITEMS_PER_ROW - 1;
            }
         }
         this.mcPaginationBar.GotoPrevPage();
         if(_loc2_ >= 0)
         {
            this.mCategoryInput.SetHighlightedIndex(_loc2_,true);
         }
      }
      
      protected function HandlePageRight(param1:Boolean = false) : void
      {
         var _loc3_:int = 0;
         var _loc4_:int = 0;
         var _loc5_:int = 0;
         var _loc6_:int = 0;
         var _loc7_:int = 0;
         var _loc8_:int = 0;
         var _loc9_:int = 0;
         var _loc10_:int = 0;
         var _loc11_:int = 0;
         var _loc12_:int = 0;
         var _loc13_:int = 0;
         var _loc2_:int = -1;
         if(NavManager.Instance.CurrentFocusable == this.mCategoryInput && this.mCategoryPageFeed.CanAdvancePage(1))
         {
            _loc3_ = this.mCategoryInput.GetHighlightedIndex();
            _loc4_ = this.mCategoryPageFeed.NumCategoriesPerPage;
            _loc5_ = SimInfoTrayTunables.PHONE_CATEGORY_GRID_ITEMS_PER_ROW;
            _loc6_ = this.mCategoryPageFeed.length;
            _loc7_ = this.mCategoryPageFeed.CurrentPage * _loc4_ + _loc3_;
            _loc8_ = _loc7_ + _loc4_;
            if(param1)
            {
               _loc9_ = -_loc5_ + 1;
               _loc10_ = _loc8_ + _loc9_;
               if(_loc10_ < _loc6_)
               {
                  _loc2_ = _loc3_ + _loc9_;
               }
               else
               {
                  _loc11_ = _loc6_ % _loc5_;
                  _loc12_ = _loc11_ > 0 ? int(_loc6_ - _loc11_) : int(_loc6_ - _loc5_);
                  _loc2_ = this.mCategoryPageFeed.RequestIndexPerPage(_loc12_);
               }
            }
            else if(_loc8_ >= _loc6_)
            {
               _loc13_ = int(_loc8_ / _loc5_) - int((_loc6_ - 1) / _loc5_);
               _loc12_ = Math.min(_loc8_ - _loc13_ * _loc5_,_loc6_ - 1);
               _loc2_ = this.mCategoryPageFeed.RequestIndexPerPage(_loc12_);
            }
            else
            {
               _loc2_ = this.mCategoryPageFeed.RequestIndexPerPage(_loc8_);
            }
         }
         this.mcPaginationBar.GotoNextPage();
         if(_loc2_ >= 0)
         {
            this.mCategoryInput.SetHighlightedIndex(_loc2_,true);
         }
      }
      
      public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         return this.mCategoryInput.Enter(param1);
      }
      
      public function Exit() : void
      {
         this.mCategoryInput.Exit();
         this.mToolInput.Exit();
         this.mPaginationInput.Exit();
      }
      
      public function OnInputEventCall(param1:String, param2:Function) : IInputAdapter
      {
         this.mCategoryInput.OnInputEventCall(param1,param2);
         this.mToolInput.OnInputEventCall(param1,param2);
         this.mPaginationInput.OnInputEventCall(param1,param2);
         return this;
      }
      
      public function TryRemoveScreenFocus() : void
      {
         if(!SystemUtils.UsingConsoleInputMode)
         {
            return;
         }
         NavManager.Instance.RemoveFromFocusStack(this.mCategoryInput);
         NavManager.Instance.RemoveFromFocusStack(this.mToolInput);
         NavManager.Instance.RemoveFromFocusStack(this.mPaginationInput);
      }
   }
}


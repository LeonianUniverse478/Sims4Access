package widgets.GameEntry.Dock.controls
{
   import flash.display.DisplayObject;
   import flash.display.MovieClip;
   import flash.display.Sprite;
   import flash.events.Event;
   import flash.events.MouseEvent;
   import flash.geom.Point;
   import gamedata.GameEntry.Neighborhood.NeighborhoodLotData;
   import gamedata.GameEntry.shared.HouseholdData;
   import gamedata.GameEntry.shared.ShowPlexView;
   import gamedata.Gameplay.shared.GameplayStateData;
   import olympus.audio.Audio;
   import olympus.constants.ActionCodes;
   import olympus.constants.KeyCodes;
   import olympus.constants.ScaleMode;
   import olympus.controls.GUIComponent;
   import olympus.controls.IconComponent;
   import olympus.core.cursors.Cursors;
   import olympus.events.GenericEvent;
   import olympus.events.PushButtonEvent;
   import olympus.extensions.AudioExtension;
   import olympus.gamepad.EnterParams;
   import olympus.gamepad.LayoutAPI;
   import olympus.gamepad.NavManager;
   import olympus.gui.buttons.Button;
   import olympus.input.IInputAdapter;
   import olympus.input.IInputFocusable;
   import olympus.input.InputAction;
   import olympus.input.InputTrigger;
   import olympus.input.adapters.DynamicOmniPointAdapter;
   import olympus.input.adapters.InputAdapterConfirmEvent;
   import olympus.input.adapters.InputAdapterEvent;
   import olympus.io.CommunicationManager;
   import olympus.io.InputActionManager;
   import olympus.io.TelemetryAttribute;
   import olympus.io.TelemetryManager;
   import olympus.localization.KeysGE;
   import olympus.utils.ArrayUtils;
   import olympus.utils.ImageUtils;
   import olympus.utils.SystemUtils;
   import olympus.utils.WidgetUtils;
   import scaleform.gfx.MouseEventEx;
   import widgets.GameEntry.Dock.constants.GEDockTunables;
   import widgets.GameEntry.Neighborhood.constants.LotHighlightModes;
   import widgets.GameEntry.Neighborhood.controls.WorldHeader;
   import widgets.GameEntry.shared.HouseholdUtils;
   import widgets.shared.GENeighborhoodStateManager;
   
   [Embed(source="/_assets/assets.swf", symbol="symbol328")]
   public class PlexLotSelectOverlay extends GUIComponent implements IInputAdapter
   {
      
      protected static const OVERLAY_IMAGE_URL:String = "img://plex/ShowcaseAdditiveImage";
      
      protected static const COMMON_AREA_PLEXID:uint = 255;
      
      public var btnBack:Button;
      
      public var mcWorldHeader:WorldHeader;
      
      public var mcBackground:Sprite;
      
      public var mcFloorSelect:MovieClip;
      
      public var mcThumb:IconComponent;
      
      public var mcThumbOverlayAdd:IconComponent;
      
      public var mcThumbOverlayNorm:IconComponent;
      
      protected var btnFloorUp:Button;
      
      protected var btnFloorDown:Button;
      
      protected var mMaxLevel:int;
      
      protected var mMinLevel:int;
      
      protected var mCurrentLevel:int;
      
      protected var mPageUpKeyAction:InputAction;
      
      protected var mPageDownKeyAction:InputAction;
      
      protected var mLotDataList:Array;
      
      protected var mOverPlexId:uint;
      
      protected var mSelectedPlexId:uint;
      
      protected var mPlexIdToClipMap:Object;
      
      protected var mPlexColorMap:Array = new Array();
      
      protected var mMainInput:DynamicOmniPointAdapter;
      
      public function PlexLotSelectOverlay()
      {
         super();
         this.visible = false;
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.mMainInput = new DynamicOmniPointAdapter(null);
         }
      }
      
      override protected function ConfigUI() : void
      {
         super.ConfigUI();
         this.btnFloorUp = this.mcFloorSelect.btnFloorUp;
         this.btnFloorDown = this.mcFloorSelect.btnFloorDown;
         this.btnBack.AudioExt.ElementName = "PlexBackButton";
         this.btnBack.addEventListener(PushButtonEvent.CLICK,this.OnBackClick,false,0,true);
         this.btnFloorUp.AudioExt.ElementName = "FloorUpButton";
         this.btnFloorUp.TooltipExt.SetText(KeysGE.PLEX_LOT_SELECT_FLOOR_UP_TOOLTIP);
         this.btnFloorUp.addEventListener(PushButtonEvent.CLICK,this.OnFloorUpClick,false,0,true);
         this.btnFloorDown.AudioExt.ElementName = "FloorDownButton";
         this.btnFloorDown.TooltipExt.SetText(KeysGE.PLEX_LOT_SELECT_FLOOR_DOWN_TOOLTIP);
         this.btnFloorDown.addEventListener(PushButtonEvent.CLICK,this.OnFloorDownClick,false,0,true);
         this.mPageUpKeyAction = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.PAGE_UP)).AllowWhileModalOpen(true).CallFunction(this.OnFloorUpClick);
         this.mPageDownKeyAction = InputAction.WhenTriggered(InputTrigger.FromKeyBinding(KeyCodes.PAGE_DOWN)).AllowWhileModalOpen(true).CallFunction(this.OnFloorDownClick);
         this.mcThumb.addEventListener(MouseEvent.MOUSE_MOVE,this.OnMouseMoveOverImage,false,0,true);
         this.mcThumb.addEventListener(MouseEvent.MOUSE_OUT,this.OnMouseOutImage,false,0,true);
         this.mcThumb.addEventListener(MouseEvent.CLICK,this.OnClickImage,false,0,true);
         var _loc1_:AudioExtension = this.mcThumb.AddExtension(AudioExtension) as AudioExtension;
         _loc1_.ElementName = "PlexSelect";
         _loc1_.Hookup(MouseEvent.CLICK,Audio.CUSTOM);
         this.mcThumb.scaleMode = ScaleMode.EXACT_FIT;
         this.mcThumbOverlayAdd.scaleMode = ScaleMode.EXACT_FIT;
         this.mcThumbOverlayAdd.mouseEnabled = false;
         this.mcThumbOverlayNorm.scaleMode = ScaleMode.EXACT_FIT;
         this.mcThumbOverlayNorm.mouseEnabled = false;
         if(SystemUtils.UsingConsoleInputMode)
         {
            this.InitGamepad();
         }
      }
      
      override protected function OnRemovedFromStage(param1:Event) : void
      {
         var _loc2_:NeighborhoodLotData = null;
         var _loc3_:Object = null;
         var _loc4_:PlexClip = null;
         super.OnRemovedFromStage(param1);
         if(Boolean(this.mPageDownKeyAction) && Boolean(this.mPageUpKeyAction))
         {
            InputActionManager.UnregisterAction(this.mPageDownKeyAction);
            InputActionManager.UnregisterAction(this.mPageUpKeyAction);
         }
         CommunicationManager.SendUIMessage("SetControlPanelButtonsEnabled",{"bEnabled":true});
         if(SystemUtils.UsingConsoleInputMode)
         {
            for each(_loc2_ in this.mLotDataList)
            {
               _loc3_ = this.mPlexIdToClipMap[_loc2_.plexId];
               if(_loc3_)
               {
                  _loc4_ = _loc3_.plexClip as PlexClip;
                  if(_loc4_)
                  {
                     _loc4_.removeEventListener(MouseEvent.ROLL_OVER,this.HandlePlexClipRollover);
                     _loc4_.removeEventListener(MouseEvent.ROLL_OUT,this.HandlePlexClipRollout);
                  }
               }
            }
         }
      }
      
      override public function set visible(param1:Boolean) : void
      {
         super.visible = param1;
         if(visible)
         {
            InputActionManager.RegisterAction(this.mPageDownKeyAction);
            InputActionManager.RegisterAction(this.mPageUpKeyAction);
         }
         else if(Boolean(this.mPageDownKeyAction) && Boolean(this.mPageUpKeyAction))
         {
            InputActionManager.UnregisterAction(this.mPageDownKeyAction);
            InputActionManager.UnregisterAction(this.mPageUpKeyAction);
         }
      }
      
      public function GetLotDataList() : Array
      {
         return this.mLotDataList;
      }
      
      public function Show(param1:Array, param2:ShowPlexView = null, param3:Object = null) : void
      {
         var _loc4_:int = 0;
         var _loc5_:HouseholdData = null;
         var _loc6_:Object = null;
         var _loc7_:Object = null;
         var _loc8_:NeighborhoodLotData = null;
         var _loc9_:GENeighborhoodStateManager = null;
         var _loc10_:Object = null;
         var _loc11_:PlexClip = null;
         var _loc12_:Object = null;
         var _loc13_:int = 0;
         if(!param1.length)
         {
            return;
         }
         if(visible)
         {
            this.CleanUp();
         }
         this.mLotDataList = param1;
         this.mPlexIdToClipMap = new Object();
         this.mMinLevel = int.MAX_VALUE;
         this.mMaxLevel = int.MIN_VALUE;
         _loc6_ = new Object();
         this.btnBack.visible = param2 == null && !SystemUtils.UsingController;
         if(param2)
         {
            _loc4_ = this.mcWorldHeader.Mode = param2.mMode;
            _loc5_ = GameplayStateData.ActiveHouseholdData;
            this.mcWorldHeader.FamilyName = _loc5_.familyName;
            this.mcWorldHeader.TravelingWithNonHouseholdSims = HouseholdUtils.IsTravelingWithNonHouseholdSims(_loc5_,param2.traveling_sim_ids);
            if(param2.mExchangeData)
            {
               this.mcWorldHeader.ExchangeId = param2.mExchangeData.id;
            }
         }
         else
         {
            _loc9_ = GENeighborhoodStateManager.getInstance();
            _loc4_ = _loc9_.Mode;
            _loc5_ = _loc9_.ActiveHousehold;
            _loc8_ = param1[0] as NeighborhoodLotData;
            this.mcWorldHeader.PlexTitle = _loc8_.IsMultiUnitBuildingSharedZone && _loc8_.lotName != null && _loc8_.lotName.length > 0 ? _loc8_.lotName : _loc8_.lotDescriptionData.name.toString();
         }
         if(_loc5_)
         {
            _loc7_ = CommunicationManager.CallGameService("GetFamilyLastPlayedSimInfo",_loc5_.familyId);
         }
         this.mPlexColorMap = new Array();
         for each(_loc8_ in param1)
         {
            _loc10_ = param3 ? param3[_loc8_.zoneInstanceId] : null;
            _loc11_ = new PlexClip();
            addChild(_loc11_);
            if(this.mPlexIdToClipMap[_loc8_.plexId] == null)
            {
               _loc12_ = this.mPlexIdToClipMap[_loc8_.plexId] = new Object();
            }
            else
            {
               _loc12_ = this.mPlexIdToClipMap[_loc8_.plexId];
            }
            _loc12_.plexClip = _loc11_;
            if(Boolean(_loc10_) && Boolean(_loc10_["disabledTooltip"]))
            {
               _loc6_ = {"TooltipString":_loc10_["disabledTooltip"]};
               _loc12_.enabled = false;
            }
            else
            {
               _loc6_ = {
                  "Mode":_loc4_,
                  "ActiveHH":_loc5_,
                  "LotData":_loc8_
               };
               _loc12_.enabled = true;
            }
            _loc11_.SetupLotRollover(_loc8_,_loc6_);
            if(Boolean(_loc10_) && Boolean(_loc10_["highlightMode"]))
            {
               _loc13_ = int(_loc10_["highlightMode"]);
            }
            else
            {
               _loc13_ = LotHighlightModes.EDIT;
            }
            this.mPlexColorMap.push({
               "plexId":_loc8_.plexId,
               "colorValue":LotHighlightModes.GetColorForHighlightMode(_loc13_,true)
            });
            if(_loc8_.IsMultiUnitBuilding)
            {
               if(this.mMinLevel > _loc8_.plexMinLevel)
               {
                  this.mMinLevel = _loc8_.plexMinLevel;
               }
               if(this.mMaxLevel < _loc8_.plexMaxLevel)
               {
                  this.mMaxLevel = _loc8_.plexMaxLevel;
               }
            }
            if(SystemUtils.UsingConsoleInputMode)
            {
               _loc11_.addEventListener(MouseEvent.ROLL_OVER,this.HandlePlexClipRollover,false,0,true);
               _loc11_.addEventListener(MouseEvent.ROLL_OUT,this.HandlePlexClipRollout,false,0,true);
            }
            _loc11_.mcSimThumbnail.visible = false;
            if(_loc7_)
            {
               if(_loc8_.zoneInstanceId == _loc7_.currentLotId)
               {
                  _loc11_.mcSimThumbnail.visible = true;
                  ImageUtils.LoadSimThumbnail(_loc11_.mcSimThumbnail.mcThumbnail,_loc7_.id,ImageUtils.SIM_THUMBNAIL_TYPE_FACE,ImageUtils.THUMBNAIL_SIZE_MEDIUM);
               }
            }
         }
         if(!_loc8_.IsMultiUnitBuilding)
         {
            this.mMinLevel = _loc8_.plexMinLevel;
            this.mMaxLevel = _loc8_.plexMaxLevel;
         }
         this.mCurrentLevel = this.mMinLevel < 0 ? 0 : this.mMinLevel;
         if(this.mMinLevel == this.mMaxLevel)
         {
            this.mcFloorSelect.visible = false;
         }
         else
         {
            this.mcFloorSelect.visible = true;
            this.btnFloorDown.enabled = this.mCurrentLevel != this.mMinLevel;
            this.btnFloorUp.enabled = this.mCurrentLevel != this.mMaxLevel;
         }
         this.SetupOverlay();
         this.LoadThumbnail();
         if(!visible)
         {
            this.visible = true;
         }
         this.HandleStageResized(LayoutAPI.StageWidth,LayoutAPI.StageHeight);
         CommunicationManager.SendUIMessage("SetControlPanelButtonsEnabled",{"bEnabled":false});
         if(SystemUtils.UsingController)
         {
            NavManager.Instance.FocusWidgetForward(WidgetUtils.GetBaseName(this),{"focusPlex":true});
         }
         if(SystemUtils.UsingConsoleInputMode)
         {
            CommunicationManager.AddMessageListener("PostUsingControllerToggled",this.HandlePostUsingControllerToggled,this);
         }
      }
      
      public function Hide(param1:Boolean = false) : void
      {
         if(!visible)
         {
            return;
         }
         this.CleanUp();
         this.visible = false;
         if(Boolean(this.mLotDataList) && this.mLotDataList.length > 0)
         {
            CommunicationManager.SendUIMessage("ResidentialDeselected",(this.mLotDataList[0] as NeighborhoodLotData).lotDescriptionId);
            this.mLotDataList = null;
         }
         if(param1)
         {
            dispatchEvent(new GenericEvent(GenericEvent.CLOSE));
         }
         CommunicationManager.SendUIMessage("SetControlPanelButtonsEnabled",{"bEnabled":true});
         if(SystemUtils.UsingController)
         {
            NavManager.Instance.FocusBack();
         }
         if(SystemUtils.UsingConsoleInputMode)
         {
            CommunicationManager.RemoveMessageListener("PostUsingControllerToggled",this.HandlePostUsingControllerToggled,this);
         }
      }
      
      public function UpdateLotName(param1:String, param2:String) : void
      {
         var _loc3_:NeighborhoodLotData = null;
         if(this.mLotDataList)
         {
            _loc3_ = this.mLotDataList[ArrayUtils.IndexOfByFieldName(this.mLotDataList,"zoneInstanceId",param1)] as NeighborhoodLotData;
            if(_loc3_)
            {
               _loc3_.lotName = param2;
            }
         }
      }
      
      public function UpdateLotData(param1:NeighborhoodLotData) : void
      {
         var _loc2_:NeighborhoodLotData = null;
         if(this.mLotDataList)
         {
            _loc2_ = this.mLotDataList[ArrayUtils.IndexOfByFieldName(this.mLotDataList,"zoneInstanceId",param1.zoneInstanceId)] as NeighborhoodLotData;
            if(_loc2_)
            {
               _loc2_.UpdateZoneData(param1);
            }
         }
      }
      
      protected function CleanUp() : void
      {
         var _loc1_:String = null;
         var _loc2_:PlexClip = null;
         this.mcWorldHeader.PlexTitle = this.mcWorldHeader.ExchangeId = this.mcWorldHeader.FamilyName = null;
         this.mcWorldHeader.Mode = -1;
         this.mcWorldHeader.TravelingWithNonHouseholdSims = false;
         this.mOverPlexId = 0;
         this.mSelectedPlexId = 0;
         this.mCurrentLevel = 0;
         this.mcBackground.removeEventListener(MouseEvent.CLICK,this.OnClickBackground);
         for(_loc1_ in this.mPlexIdToClipMap)
         {
            _loc2_ = this.mPlexIdToClipMap[_loc1_].plexClip;
            removeChild(_loc2_);
            this.mPlexIdToClipMap[_loc1_] = null;
         }
      }
      
      public function HandleStageResized(param1:Number, param2:Number) : void
      {
         var _loc4_:Number = NaN;
         if(!visible)
         {
            return;
         }
         this.mcBackground.width = param1;
         this.mcBackground.height = param2;
         var _loc3_:Number = param1 * 0.5;
         _loc4_ = param2 * 0.5;
         this.mcThumb.x = _loc3_ - GEDockTunables.PLEX_SELECTOR_THUMBNAIL_SIZE.x * 0.5;
         this.mcThumb.y = _loc4_ - GEDockTunables.PLEX_SELECTOR_THUMBNAIL_SIZE.y * 0.5;
         this.mcThumbOverlayAdd.x = this.mcThumbOverlayNorm.x = this.mcThumb.x;
         this.mcThumbOverlayAdd.y = this.mcThumbOverlayNorm.y = this.mcThumb.y;
         this.mcWorldHeader.RefreshState(false,param1 - GEDockTunables.PLEX_SELECTOR_SPACING * 2);
         this.mcWorldHeader.x = _loc3_ - this.mcWorldHeader.width * 0.5;
         this.mcFloorSelect.x = this.mcThumb.x + GEDockTunables.PLEX_SELECTOR_THUMBNAIL_SIZE.x + GEDockTunables.PLEX_SELECTOR_FLOOR_BUTTON_OFFSET;
         this.mcFloorSelect.y = _loc4_ - this.mcFloorSelect.height * 0.5;
         this.PositionPlexClips();
      }
      
      // Accessibility uses the same clip identity and eligibility map as EA.
      public function A11yPlexInfo(clip:DisplayObject) : Object
      {
         if(!this.visible || clip == null || !clip.visible || clip.parent != this || !(clip is PlexClip)) { return null; }
         var id:uint = this.GetPlexIDForClip(clip as PlexClip);
         var index:int = ArrayUtils.IndexOfByFieldName(this.mLotDataList,"plexId",id);
         if(id == 0 || index < 0 || this.mPlexIdToClipMap[id] == null) { return null; }
         return {"id":id,"lot":this.mLotDataList[index],"enabled":this.mPlexIdToClipMap[id].enabled,"selected":id == this.mSelectedPlexId,"floor":this.mCurrentLevel};
      }

      public function A11yPlexSelect(clip:DisplayObject) : Boolean
      {
         var info:Object = this.A11yPlexInfo(clip);
         if(info == null || info.enabled != true) { return false; }
         this.SetOverPlexId(uint(info.id));
         this.OnClickImage(null);
         return this.mSelectedPlexId == uint(info.id);
      }

      public function get OverPlexId() : int
      {
         return this.mOverPlexId;
      }
      
      public function ClearSelectedPlexId() : void
      {
         this.SetSelectedPlexId(0);
      }
      
      protected function SetOverPlexId(param1:int) : void
      {
         var _loc2_:NeighborhoodLotData = null;
         if(this.mOverPlexId == param1)
         {
            return;
         }
         if(this.mOverPlexId > 0 && Boolean(this.mPlexIdToClipMap[this.mOverPlexId]))
         {
            (this.mPlexIdToClipMap[this.mOverPlexId].plexClip as PlexClip).DoRollout();
         }
         this.mOverPlexId = param1;
         if(param1 > 0 && Boolean(this.mPlexIdToClipMap[param1]))
         {
            (this.mPlexIdToClipMap[param1].plexClip as PlexClip).DoRollover();
         }
      }
      
      protected function SetSelectedPlexId(param1:int) : void
      {
         this.mSelectedPlexId = param1;
         if(param1 == 0)
         {
            this.mcBackground.addEventListener(MouseEvent.CLICK,this.OnClickBackground,false,0,true);
         }
         else
         {
            this.mcBackground.removeEventListener(MouseEvent.CLICK,this.OnClickBackground);
         }
      }
      
      protected function IncrementFloorLevel(param1:int) : void
      {
         var _loc2_:Boolean = false;
         if(SystemUtils.UsingController && Boolean(this.mOverPlexId))
         {
            _loc2_ = true;
            this.HandlePlexClipRollout();
         }
         this.mCurrentLevel += param1;
         this.LoadThumbnail();
         this.SetupOverlay();
         this.btnFloorUp.enabled = this.mCurrentLevel != this.mMaxLevel;
         this.btnFloorDown.enabled = this.mCurrentLevel != this.mMinLevel;
         if(SystemUtils.UsingController && _loc2_)
         {
            this.mMainInput.HighlightClosestToPoint(new Point(),true);
         }
         var _loc3_:Array = [new TelemetryAttribute("flud",param1 > 0 ? 1 : 0)];
         TelemetryManager.DispatchTelemetryEvent("GAME","GEDK","PLFL",_loc3_);
      }
      
      protected function LoadThumbnail() : void
      {
         if(!this.mLotDataList || !this.mLotDataList.length)
         {
            this.mcThumb.visible = false;
            this.mcThumbOverlayAdd.visible = false;
            this.mcThumbOverlayNorm.visible = false;
            return;
         }
         this.mcThumb.visible = true;
         this.mcThumbOverlayAdd.visible = true;
         this.mcThumbOverlayNorm.visible = true;
         var _loc1_:NeighborhoodLotData = this.mLotDataList[0] as NeighborhoodLotData;
         ImageUtils.LoadPlexPreviewThumbnail(this.mcThumb,_loc1_.masterZoneId,_loc1_.lotDescriptionId,this.mCurrentLevel);
         this.mcThumbOverlayAdd.LoadImage(OVERLAY_IMAGE_URL);
         this.mcThumbOverlayNorm.LoadImage(OVERLAY_IMAGE_URL);
      }
      
      protected function SetupOverlay() : void
      {
         var _loc4_:Object = null;
         var _loc5_:Object = null;
         var _loc6_:int = 0;
         this.mOverPlexId = 0;
         this.SetSelectedPlexId(0);
         var _loc1_:NeighborhoodLotData = this.mLotDataList[0] as NeighborhoodLotData;
         var _loc2_:Object = {
            "zoneInstanceId":_loc1_.masterZoneId,
            "lotDescriptionId":_loc1_.lotDescriptionId,
            "level":this.mCurrentLevel,
            "plexColorMap":this.mPlexColorMap
         };
         var _loc3_:Array = CommunicationManager.CallGameService("PlexSetupOverlay",_loc2_) as Array;
         for each(_loc4_ in this.mPlexIdToClipMap)
         {
            _loc4_.plexPos = null;
         }
         for each(_loc5_ in _loc3_)
         {
            _loc6_ = int(_loc5_.plexId);
            if(_loc1_.IsMultiUnitBuilding && _loc6_ != 0)
            {
               _loc6_ += 256;
            }
            if(this.mPlexIdToClipMap[_loc6_])
            {
               this.mPlexIdToClipMap[_loc6_].plexPos = new Point(_loc5_.position.x,_loc5_.position.y);
            }
         }
         this.PositionPlexClips();
      }
      
      protected function PositionPlexClips() : void
      {
         var _loc1_:String = null;
         var _loc2_:PlexClip = null;
         var _loc3_:Point = null;
         if(!this.mPlexIdToClipMap)
         {
            return;
         }
         for(_loc1_ in this.mPlexIdToClipMap)
         {
            _loc2_ = this.mPlexIdToClipMap[_loc1_].plexClip;
            _loc3_ = this.mPlexIdToClipMap[_loc1_].plexPos;
            if(_loc3_)
            {
               _loc2_.visible = true;
               _loc2_.x = this.mcThumb.x + this.mPlexIdToClipMap[_loc1_].plexPos.x;
               _loc2_.y = this.mcThumb.y + this.mPlexIdToClipMap[_loc1_].plexPos.y;
            }
            else
            {
               _loc2_.visible = false;
            }
         }
      }
      
      protected function OnBackClick(param1:PushButtonEvent) : void
      {
         this.Hide(true);
      }
      
      protected function OnFloorUpClick(param1:PushButtonEvent = null) : void
      {
         if(this.mCurrentLevel != this.mMaxLevel)
         {
            this.IncrementFloorLevel(1);
         }
      }
      
      protected function OnFloorDownClick(param1:PushButtonEvent = null) : void
      {
         if(this.mCurrentLevel != this.mMinLevel)
         {
            this.IncrementFloorLevel(-1);
         }
      }
      
      protected function OnMouseMoveOverImage(param1:MouseEvent) : void
      {
         var _loc2_:Number = Math.round(param1.localX);
         var _loc3_:Number = Math.round(param1.localY);
         var _loc4_:uint = CommunicationManager.CallGameService("PlexMouseOver",{
            "mouseX":_loc2_,
            "mouseY":_loc3_
         }) as uint;
         if(Boolean(this.mLotDataList) && Boolean(this.mLotDataList[0].IsMultiUnitBuilding) && _loc4_ != 0)
         {
            _loc4_ += 256;
         }
         Cursors.SetCursor(_loc4_ > 0 && _loc4_ != COMMON_AREA_PLEXID ? Cursors.BUTTON_OVER : null);
         this.SetOverPlexId(_loc4_);
      }
      
      protected function OnMouseOutImage(param1:MouseEvent) : void
      {
         Cursors.SetCursor(null);
         CommunicationManager.CallGameService("PlexMouseOver",{
            "mouseX":0,
            "mouseY":0
         });
         this.SetOverPlexId(0);
      }
      
      protected function OnClickBackground(param1:MouseEvent) : *
      {
         if(this.mSelectedPlexId == 0)
         {
            this.OnBackClick(null);
         }
      }
      
      protected function OnClickImage(param1:MouseEvent) : void
      {
         var _loc2_:MouseEventEx = param1 as MouseEventEx;
         if(Boolean(_loc2_) && _loc2_.buttonIdx != MouseEventEx.LEFT_BUTTON)
         {
            return;
         }
         if(this.mOverPlexId == 0)
         {
            this.OnClickBackground(param1);
            return;
         }
         var _loc3_:int = ArrayUtils.IndexOfByFieldName(this.mLotDataList,"plexId",this.mOverPlexId);
         if(_loc3_ > -1 && this.mOverPlexId != this.mSelectedPlexId)
         {
            if(this.mPlexIdToClipMap[this.mOverPlexId].enabled)
            {
               this.SetSelectedPlexId(this.mOverPlexId);
               CommunicationManager.SendUIMessage("LotSelected",{"lotData":this.mLotDataList[_loc3_]});
            }
         }
      }
      
      protected function InitGamepad() : void
      {
         this.btnBack.visible = false;
         this.mMainInput.SetContainer(this);
         this.mMainInput.ElementShouldBeAddedCheck = this.MainElementShouldBeAddedCheck;
         this.mMainInput.OnEnteredCall(this.HandleMainEntered);
         this.mMainInput.IgnoreDefaultAction(ActionCodes.NAVIGATE_DOWN);
         this.mMainInput.IgnoreDefaultAction(ActionCodes.NAVIGATE_UP);
         var _loc1_:InputAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.NAVIGATE_UP)).AllowWhileModalOpen(true).CallFunction(this.HandleFloorUpAction).SetLegendKey(KeysGE.PLEX_LOT_SELECT_FLOOR_UP_TOOLTIP);
         var _loc2_:InputAction = InputAction.WhenTriggered(InputTrigger.FromActionCode(ActionCodes.NAVIGATE_DOWN)).AllowWhileModalOpen(true).CallFunction(this.HandleFloorDownAction).SetLegendKey(KeysGE.PLEX_LOT_SELECT_FLOOR_DOWN_TOOLTIP);
         this.mMainInput.AddInputActions([_loc1_,_loc2_]);
      }
      
      protected function MainElementShouldBeAddedCheck(param1:DisplayObject) : Boolean
      {
         return param1 is PlexClip || param1 == this.btnFloorUp || param1 == this.btnFloorDown;
      }
      
      protected function HandleMainEntered() : void
      {
         this.mMainInput.HighlightClosestToPoint(new Point(),true);
      }
      
      protected function HandlePlexClipRollover(param1:MouseEvent = null) : void
      {
         var _loc3_:uint = 0;
         var _loc4_:Point = null;
         if(!SystemUtils.UsingController)
         {
            return;
         }
         var _loc2_:PlexClip = param1.currentTarget as PlexClip;
         if(_loc2_)
         {
            _loc3_ = this.GetPlexIDForClip(_loc2_);
            if(_loc3_ > 0)
            {
               _loc4_ = this.mPlexIdToClipMap[_loc3_].plexPos;
               this.mcThumb.dispatchEvent(new MouseEvent(MouseEvent.MOUSE_MOVE,true,false,_loc4_.x,_loc4_.y));
            }
         }
      }
      
      protected function HandlePlexClipRollout(param1:MouseEvent = null) : void
      {
         if(!SystemUtils.UsingController)
         {
            return;
         }
         this.mcThumb.dispatchEvent(new MouseEvent(MouseEvent.MOUSE_OUT,true,false,0,0));
      }
      
      protected function HandleFloorUpAction() : void
      {
         if(this.btnFloorUp.enabled)
         {
            this.OnFloorUpClick();
         }
      }
      
      protected function HandleFloorDownAction() : void
      {
         if(this.btnFloorDown.enabled)
         {
            this.OnFloorDownClick();
         }
      }
      
      protected function GetPlexIDForClip(param1:PlexClip) : uint
      {
         var _loc2_:String = null;
         for(_loc2_ in this.mPlexIdToClipMap)
         {
            if(this.mPlexIdToClipMap[_loc2_].plexClip == param1)
            {
               return uint(_loc2_);
            }
         }
         return 0;
      }
      
      public function Enter(param1:EnterParams = null) : IInputFocusable
      {
         this.mMainInput.Enter(param1);
         return this;
      }
      
      public function Exit() : void
      {
         this.mMainInput.Exit();
      }
      
      public function OnInputEventCall(param1:String, param2:Function) : IInputAdapter
      {
         var inputEventType:String = param1;
         var callback:Function = param2;
         var callbackFunc:Function = callback;
         if(inputEventType == InputAdapterEvent.CONFIRM)
         {
            callbackFunc = function(param1:InputAdapterConfirmEvent):void
            {
               if(param1.GetObj() is PlexClip)
               {
                  OnClickImage(null);
                  callback(param1);
               }
            };
         }
         this.mMainInput.OnInputEventCall(inputEventType,callbackFunc);
         return this;
      }
      
      protected function HandlePostUsingControllerToggled() : void
      {
         if(SystemUtils.UsingController)
         {
            NavManager.Instance.FocusWidgetForward(WidgetUtils.GetBaseName(this),{"focusPlex":true});
         }
      }
   }
}


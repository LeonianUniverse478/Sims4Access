      // Insert this helper in TooltipManager. In A11yFocusInto, immediately
      // before mA11yPendingScope = param1, call:
      // if(this.mA11yPendingScope != param1) { this.A11yFenceOpeningInput(); }
      // The startup bridge must permit the same no-argument command.
      public function A11yFenceOpeningInput() : void
      {
         try
         {
            CommunicationManager.PostServerCommand("a11y.inputfence","");
         }
         catch(e:Error) { }
      }

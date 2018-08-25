/**
 * (C) Copyright 2010, 2011 upTick Pty Ltd
 * 
 * Licensed under the terms of the GNU General Public License version 3 
 * as published by the Free Software Foundation. You may obtain a copy of the
 * License at: http://www.gnu.org/copyleft/gpl.html
 * 
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
 * WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
 * License for the specific language governing permissions and limitations 
 * under the License.
 */

package au.com.uptick.serendipity.client.resourcecentre.view;

import com.google.gwt.user.client.ui.Widget;
import com.google.inject.Inject;

import com.gwtplatform.mvp.client.ViewImpl;

import com.smartgwt.client.types.ContentsType;
import com.smartgwt.client.widgets.HTMLPane;

import com.smartgwt.client.widgets.layout.VLayout;

import com.allen_sauer.gwt.log.client.Log;

import au.com.uptick.serendipity.client.resourcecentre.presenter.HighlightsPresenter;

public class HighlightsView extends ViewImpl implements HighlightsPresenter.MyView {
  
  private static final String CONTEXT_AREA_WIDTH = "*";  
  private static final String CONTEXT_AREA_HEIGHT = "100%";  

  private VLayout panel; 
  private HTMLPane htmlPane;
  
  @Inject
  public HighlightsView() {
    
    Log.debug("HighlightsView()");   
    
    panel = new VLayout();
    
    // initialise the HighlightsView layout container
    panel.setStyleName("crm-ContextArea");
    panel.setWidth(CONTEXT_AREA_WIDTH); 
    panel.setHeight(CONTEXT_AREA_HEIGHT);
       
    htmlPane = new HTMLPane();
    htmlPane.setContentsURL("http://code.google.com/p/crmdipity/");
    htmlPane.setContentsType(ContentsType.PAGE);
    
    panel.addMember(htmlPane);
  }

  @Override
  public Widget asWidget() {
    return panel;
  }
}

/*

    panel.addResizedHandler(new ResizedHandler() {
      @Override
      public void onResized(ResizedEvent event) {
        Log.debug("onResized(event)");   
        
        int height = panel.getVisibleHeight();
        htmlPane.setHeight(height);
      }
    });
    
*/
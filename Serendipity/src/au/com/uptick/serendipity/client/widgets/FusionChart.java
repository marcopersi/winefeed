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

package au.com.uptick.serendipity.client.widgets;

import java.util.HashMap;

import com.smartgwt.client.widgets.plugins.Flashlet;

public class FusionChart extends Flashlet {
  
  private static int count = 0;
  
  private String swfId;

  public FusionChart(String src, String width, String height, String dataUrl) {
    super();
    
    setCodeBase("http://fpdownload.macromedia.com/pub/shockwave/cabs/flash/swflash.cab#version=8,0,0,0");
    setClassID("clsid:d27cdb6e-ae6d-11cf-96b8-444553540000");
    setPluginsPage("http://www.macromedia.com/go/getflashplayer");    
    
    swfId = "fusionChartId_" + count;
    ++count;
    
    setID(swfId);
    setName(swfId);
    setSrc("charts/fusioncharts/flash/" + src);
    setSize(width, height);
    
    HashMap<String, String> hashMap = new HashMap<String, String>();
    
    hashMap.put("id", swfId);
    hashMap.put("flashvars", "&id=" + swfId + "&chartWidth=" + width + "&chartHeight=" + height + 
        "&registerWithJS=1" + "&debugMode=0" + "&dataURL=" + "charts/fusioncharts/data/" + dataUrl);
    
    // hashMap.put("allowscriptaccess", "always");
    // hashMap.put("wmode", "opaque" ); 
    // hashMap.put("quality", "high");
    // hashMap.put("bgcolor", "#ffffff");
    
    // If you embed the chart into your web page, and the page has layers such as drop-down menus or 
    // drop-down forms, and you want them appear above the chart, you need to add the following  line 
    // to your code. 
    // hashMap.put("wmode", "opaque" ); 
    
    // "&DOMId="
    
    setParams(hashMap);
    
    // setCanSelectText(true);
  }
}

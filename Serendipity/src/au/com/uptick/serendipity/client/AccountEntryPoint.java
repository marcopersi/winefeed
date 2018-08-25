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

package au.com.uptick.serendipity.client;

import org.gwtmultipage.client.UrlPatternEntryPoint;

import com.allen_sauer.gwt.log.client.Log;
import com.gwtplatform.mvp.client.proxy.PlaceRequest;

// @UrlPatternEntryPoint(value = "(Account.html)?(\\\\?accountId=[0-9]+&activity=(new|edit))?((&|\\\\?)locale=(en|de))?")
@UrlPatternEntryPoint(value = "(Account.html)?(\\\\?accountId=([0-9a-zA-Z+/=]{4,})+&activity=([0-9a-zA-Z+/=]{4,}))?((&|\\\\?)locale=(en|de))?")
public class AccountEntryPoint extends MultiPageEntryPoint {

  protected void revealCurrentPlace(String page) {

    if (page.equals(NameTokens.accountPage)) {
      PlaceRequest placeRequest = new PlaceRequest(NameTokens.accountPage);
      getSerendipityGinjector().getPlaceManager().revealPlace(placeRequest);
    } else {
      Log.debug("Page name token: " + page);
    }
  }
}
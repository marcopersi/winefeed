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

import au.com.uptick.serendipity.shared.dto.sales.AccountsDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.gwt.junit.client.GWTTestCase;

public class AccountGWTTestCase extends GWTTestCase {

  private long startTimeMillis;
  
  @Override
  public String getModuleName() {
    // webAppCreator -out Serendipity au.com.uptick.serendipity.Serendipity
    return "au.com.uptick.serendipity.Serendipity";
  }
  
  @Override
  public void gwtSetUp() throws Exception {
    // super.gwtSetUp();
    
    if (Log.isDebugEnabled()) {
      Log.debug("Log.isDebugEnabled() == true");
      startTimeMillis = System.currentTimeMillis();
    }    
  }
  
  @Override
  public void gwtTearDown() throws Exception { 
    // super.gwtTearDown();
    
    if (Log.isDebugEnabled()) {
      long endTimeMillis = System.currentTimeMillis();
      float durationSeconds = (endTimeMillis - startTimeMillis) / 1000F;
      Log.debug("Duration: " + durationSeconds + " seconds");
    }      
  }
 
  public void testAccountDto() {
    try {
      Log.debug("testAccountDto()");

      AccountsDto upTick1 = new AccountsDto();
      upTick1.setAccountId(1L);
      upTick1.setAccountName("upTick Pty Ltd");
      Log.debug(upTick1.toString());
      
      AccountsDto upTick2 = new AccountsDto();
      upTick2.setAccountId(1L);
      upTick2.setAccountName("upTick Pty Ltd");
      Log.debug(upTick2.toString());
      
      AccountsDto shaneLongman1 = new AccountsDto();
      shaneLongman1.setAccountId(2L);
      shaneLongman1.setAccountName("Shane Longman Pty Ltd");
      Log.debug(shaneLongman1.toString());
      
      AccountsDto shaneLongman2 = new AccountsDto();
      shaneLongman2.setAccountId(2L);
      shaneLongman2.setAccountName("Shane Longman Pty Ltd");
      Log.debug(shaneLongman2.toString());
      
      assertTrue(upTick1.equals(upTick2));
      assertFalse(upTick1.equals(shaneLongman1));
      
      assertTrue(shaneLongman1.equals(shaneLongman2));
      assertFalse(shaneLongman1.equals(upTick1));
      
    } catch (Exception e) {
      Log.error("e: " + e);
      e.printStackTrace(); 
    }
  }
}

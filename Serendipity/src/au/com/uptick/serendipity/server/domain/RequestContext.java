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

package au.com.uptick.serendipity.server.domain;

public class RequestContext {
  
  private String userName;
  
  private static ThreadLocalton localton = new ThreadLocalton();

  private static class ThreadLocalton extends ThreadLocal<Object> {
    protected synchronized Object initialValue() {
      RequestContext context = new RequestContext();
      return context;
    }
  }

  private RequestContext() { }

  public static RequestContext getLocalInstance() {
    RequestContext context = (RequestContext) localton.get();
    return context;
  }

  public void initRequestContext(String userName) {
    this.userName = userName;
  }

  public void clearRequestContext() {
    this.userName = null;
  }

  public String getUserName() {
    return userName;
  }
}

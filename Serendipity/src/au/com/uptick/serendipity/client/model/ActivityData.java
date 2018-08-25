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

package au.com.uptick.serendipity.client.model;

public class ActivityData {
  
  private static ActivitiesRecord[] records;
  
  public static ActivitiesRecord[] getRecords() {
    if (records == null) {
      records = getNewRecords();
    }
    
    return records;
  }  
  
  public static ActivitiesRecord[] getNewRecords() {
    return new ActivitiesRecord[]{
      new ActivitiesRecord("task", "Task", "Get A4 Paper", "Printer", 
          "High", "01/10/2010", "30/10/2010"), 
      new ActivitiesRecord("fax", "Fax", "Send Invoice", "Consulting", 
          "High", "01/10/2010", "30/10/2010"), 
      new ActivitiesRecord("phonecall", "Phone Call", "Follow-up Call", "Meeting", 
          "Normal", "01/10/2010", "30/10/2010"),
      new ActivitiesRecord("email", "Email", "Sales Proposal", "New Product", 
          "Normal", "01/10/2010", "30/10/2010"),
      new ActivitiesRecord("letter", "Letter", "Finish Proposal", "New Client", 
          "High", "01/10/2010", "30/10/2010"),
      new ActivitiesRecord("appointment", "Appointment", "New Assignment", "New Client", 
          "High", "01/10/2010", "30/10/2010")          
    };
  }
}

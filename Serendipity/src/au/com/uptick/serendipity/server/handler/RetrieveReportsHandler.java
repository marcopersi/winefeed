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

package au.com.uptick.serendipity.server.handler;

import java.util.ArrayList;
import java.util.List;

import javax.servlet.ServletContext;
import javax.servlet.http.HttpServletRequest;

import au.com.uptick.serendipity.server.dao.ReportDao;
import au.com.uptick.serendipity.server.domain.Report;
import au.com.uptick.serendipity.shared.action.RetrieveReportsAction;
import au.com.uptick.serendipity.shared.action.RetrieveReportsResult;
import au.com.uptick.serendipity.shared.dto.sales.ReportsDto;

import com.allen_sauer.gwt.log.client.Log;
import com.google.inject.Inject;
import com.google.inject.Provider;
import com.gwtplatform.dispatch.server.ExecutionContext;
import com.gwtplatform.dispatch.server.actionhandler.ActionHandler;
import com.gwtplatform.dispatch.shared.ActionException;

// don't forget to update bindHandler() in ServerModule

public class RetrieveReportsHandler implements
    ActionHandler<RetrieveReportsAction, RetrieveReportsResult> {

  @Inject
  RetrieveReportsHandler(final ServletContext servletContext,
      final Provider<HttpServletRequest> requestProvider) {
  }

  @Override
  public RetrieveReportsResult execute(RetrieveReportsAction action,
      ExecutionContext context) throws ActionException {

    RetrieveReportsResult result = null;
    ReportDao reportDao = new ReportDao();

    // DOMConfigurator.configure("log4j.xml");

    Log.info("Retrieve Reports");

    try {
      List<Report> reports = reportDao.retrieveReports(action.getMaxResults(),
          action.getFirstResult());

      if (reports != null) {
        List<ReportsDto> reportsDtos = new ArrayList<ReportsDto>(reports.size());

        for (Report report : reports) {
          reportsDtos.add(createReportsDto(report));
        }

        result = new RetrieveReportsResult(reportsDtos);
      }
    }
    catch (Exception e) {
      Log.warn("Unable to retrieve Reports - ", e);

      throw new ActionException(e);
    }

    return result;
  }

  private ReportsDto createReportsDto(Report report) {
    return new ReportsDto(report.getReportId(), report.getReportName(), report.getEntityName(), report.getReportFilename(),
        report.getReportType(), report.getModifiedOn().toString(), report.getDescription());
  }

  @Override
  public Class<RetrieveReportsAction> getActionType() {
    return RetrieveReportsAction.class;
  }

  @Override
  public void undo(RetrieveReportsAction action, RetrieveReportsResult result,
      ExecutionContext context) throws ActionException {
  }
}
package ch.persi.vino.gui2.client.marketdata.service;


import ch.persi.vino.gui2.client.lib.GenericGwtRpcService;
import ch.persi.vino.gui2.shared.WineOffering;

import com.google.gwt.user.client.rpc.RemoteServiceRelativePath;

@RemoteServiceRelativePath("vinoDaoService")
public interface VinoDaoService extends GenericGwtRpcService<WineOffering> {

}

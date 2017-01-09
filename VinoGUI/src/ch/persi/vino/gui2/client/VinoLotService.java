package ch.persi.vino.gui2.client;

import com.google.gwt.user.client.rpc.RemoteServiceRelativePath;

import ch.persi.vino.gui2.client.lib.GenericGwtRpcService;
import ch.persi.vino.gui2.shared.AuctionLot;

@RemoteServiceRelativePath("vinoAuctionLotService")
public interface VinoLotService extends GenericGwtRpcService<AuctionLot> {

}

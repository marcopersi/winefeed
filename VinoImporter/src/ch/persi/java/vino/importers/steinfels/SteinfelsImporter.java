package ch.persi.java.vino.importers.steinfels;

import java.util.Set;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.importers.Task;

public class SteinfelsImporter implements ImportingStrategy {
	
	private Set<Task> someTasks;
	private final Logger log = LoggerFactory.getLogger(ch.persi.java.vino.importers.steinfels.SteinfelsImporter.class);
	
	public void setTasks(Set<Task> theTasks)
	{
		someTasks = theTasks;
	}
	
	@Override
	public void runImport() {
    	
		for (Task aTask : someTasks) {
			// FIXME: guarantee run in 100% sequential order, start second only if first is done
			log.info("running task:" + aTask);
			aTask.execute();
		}
		log.info("Import successfully done !");
	}
	
}

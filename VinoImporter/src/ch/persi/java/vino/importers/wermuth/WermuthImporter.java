package ch.persi.java.vino.importers.wermuth;

import ch.persi.java.vino.importers.ImportingStrategy;
import ch.persi.java.vino.importers.Task;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Set;

public class WermuthImporter implements ImportingStrategy {
	
	private Set<Task> someTasks;
	private final Logger log = LoggerFactory.getLogger(getClass());

	public void setTasks(final Set<Task> theTasks)
	{
		someTasks = theTasks;
	}

	@Override
	public void runImport() {
    	
		for (Task aTask : someTasks) {
			// FIXME: guarantee run in 100% sequential order, start second only if first is done
			log.info("running task: {}", aTask);
			aTask.execute();
		}
	}
	
}

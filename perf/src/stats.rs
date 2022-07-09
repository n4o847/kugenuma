use std::{
    fmt,
    fs::File,
    io::{self, BufRead},
};

#[derive(Debug)]
pub struct CpuStatCollection {
    all: CpuStat,
    stats: Vec<CpuStat>,
}

#[derive(Debug)]
pub struct CpuStat {
    user: usize,
}

/**
 * Read CPU statistics from /proc/stat.
 */
pub fn read_stat_cpu() -> io::Result<CpuStatCollection> {
    let file = File::open("/proc/stat")?;
    let reader = io::BufReader::new(file);
    let mut all = None;
    let mut stats = Vec::new();
    for line in reader.lines() {
        let line = line.unwrap();
        let mut iter = line.split_ascii_whitespace();
        let cpu_name = iter.next().unwrap();
        if !cpu_name.starts_with("cpu") {
            continue;
        }
        let user: usize = iter.next().unwrap().parse().unwrap();
        let stat = CpuStat { user };
        if cpu_name == "cpu" {
            all = Some(stat);
        } else {
            stats.push(stat);
        }
    }
    Ok(CpuStatCollection {
        all: all.unwrap(),
        stats,
    })
}

impl CpuStatCollection {
    pub fn diff(&self, other: &Self) -> Self {
        Self {
            all: CpuStat {
                user: self.all.user - other.all.user,
            },
            stats: self
                .stats
                .iter()
                .zip(other.stats.iter())
                .map(|(self_, other)| CpuStat {
                    user: self_.user - other.user,
                })
                .collect(),
        }
    }
}

impl fmt::Display for CpuStatCollection {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{} ", self.all)?;
        let mut iter = self.stats.iter();
        write!(f, "{}", iter.next().unwrap())?;
        for stat in iter {
            write!(f, " {}", stat)?;
        }
        Ok(())
    }
}

impl fmt::Display for CpuStat {
    fn fmt(&self, f: &mut fmt::Formatter<'_>) -> fmt::Result {
        write!(f, "{}", self.user)
    }
}
